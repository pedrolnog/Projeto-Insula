"""Serviço de orquestração de ingestão e sincronização assíncrona com o ERP Sienge."""
import asyncio
import logging
import time
import traceback
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.sienge import (
    SiengeClient,
    SiengeError,
    SiengeQuotaExceeded,
    get_sienge_client,
)
from app.clients.storage import StorageClient, get_storage_client
from app.core.config import Settings, get_settings
from app.models.diario import DiarioObra
from app.models.empresa import Empresa
from app.models.enums import (
    FaseObra,
    OrigemSincronizacao,
    StatusFoto,
    StatusSincronizacao,
)
from app.models.foto import FotoDiario
from app.models.log_sincronizacao import LogSincronizacao
from app.models.obra import Obra
from app.models.tarefa import TarefaDiario
from app.models.unidade import Unidade
from app.services.media_service import MediaService
from app.services.sienge_mapper import SiengeMapper

logger = logging.getLogger(__name__)

# Chave fixa para o PostgreSQL Advisory Lock (evita execuções concorrentes entre workers)
_PG_ADVISORY_LOCK_KEY = 904_202_601
_process_lock = asyncio.Lock()


class SyncAlreadyRunningError(Exception):
    """Indica que já existe uma rotina de sincronização em andamento."""


class SyncService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        sienge_client: SiengeClient | None = None,
        storage_client: StorageClient | None = None,
        media_service: MediaService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.sienge = sienge_client or get_sienge_client(self.settings)
        self.storage = storage_client or get_storage_client(self.settings)
        self.media = media_service or MediaService(self.settings)

    async def _adquirir_lock(self, obra_id_especifica: int | None) -> int:
        if _process_lock.locked():
            raise SyncAlreadyRunningError("Já existe uma sincronização em andamento neste processo.")
        await _process_lock.acquire()
        lock_key = _PG_ADVISORY_LOCK_KEY + (obra_id_especifica or 0)
        try:
            res = await self.db.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key}
            )
            conseguiu = bool(res.scalar_one())
        except Exception:
            _process_lock.release()
            raise
        if not conseguiu:
            _process_lock.release()
            raise SyncAlreadyRunningError(
                "Já existe uma sincronização em execução em outro worker."
            )
        return lock_key

    async def _liberar_lock(self, lock_key: int) -> None:
        try:
            await self.db.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key}
            )
            await self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao liberar advisory lock %s: %s", lock_key, exc)
        finally:
            if _process_lock.locked():
                _process_lock.release()

    async def sincronizar_tudo(
        self,
        origem: OrigemSincronizacao = OrigemSincronizacao.MANUAL,
        obra_id_especifica: int | None = None,
    ) -> LogSincronizacao:
        """Executa a rotina completa de ingestão com lock distribuído, isolamento por obra e observabilidade."""
        lock_key = await self._adquirir_lock(obra_id_especifica)
        inicio_perf = time.perf_counter()
        agora = datetime.now(UTC)

        log = LogSincronizacao(
            origem=origem,
            status=StatusSincronizacao.EXECUTANDO,
            obra_id=obra_id_especifica,
            iniciado_em=agora,
            diarios_novos=0,
            diarios_atualizados=0,
            fotos_processadas=0,
            requisicoes_sienge=0,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        log_id = log.id

        diarios_novos_total = 0
        diarios_atualizados_total = 0
        fotos_processadas_total = 0
        fotos_com_erro_total = 0
        erros_obras: list[dict[str, Any]] = []
        traceback_critico: str | None = None
        mensagem_erro: str | None = None
        houve_erro_cota = False
        houve_erro_parcial = False

        try:
            async with self.sienge:
                # 1. Ingestão e atualização cadastral das Obras/Empreendimentos
                obras_alvos = await self._sincronizar_obras(obra_id_especifica)

                # 2. Sincronização dos Diários isolada por obra
                for obra_id, sienge_building_id in obras_alvos:
                    try:
                        novos, atualizados = await self._sincronizar_diarios_obra(
                            obra_id=obra_id, sienge_building_id=sienge_building_id
                        )
                        diarios_novos_total += novos
                        diarios_atualizados_total += atualizados
                    except SiengeQuotaExceeded as exc:
                        await self.db.rollback()
                        logger.warning(
                            "Cota Sienge atingida durante diários da obra %s: %s", obra_id, exc
                        )
                        houve_erro_cota = True
                        break
                    except Exception as exc:
                        await self.db.rollback()
                        logger.exception(
                            "Falha ao sincronizar diários da obra %s", obra_id
                        )
                        houve_erro_parcial = True
                        erros_obras.append(
                            {
                                "obra_id": obra_id,
                                "sienge_building_id": sienge_building_id,
                                "erro": str(exc),
                                "traceback": traceback.format_exc(),
                            }
                        )

                # 3. Pipeline de Fotos (download, conversão WebP off-thread e upload Storage)
                if not houve_erro_cota:
                    try:
                        fotos_ok, fotos_err, cota_fotos = await self._processar_fotos_pendentes(
                            obra_id_especifica
                        )
                        fotos_processadas_total += fotos_ok
                        fotos_com_erro_total += fotos_err
                        if fotos_err > 0:
                            houve_erro_parcial = True
                        if cota_fotos:
                            houve_erro_cota = True
                    except SiengeQuotaExceeded as exc:
                        logger.warning("Cota Sienge atingida durante fotos: %s", exc)
                        houve_erro_cota = True
                    except Exception as exc:
                        await self.db.rollback()
                        logger.exception("Falha ao processar lote de fotos")
                        houve_erro_parcial = True
                        erros_obras.append(
                            {
                                "etapa": "fotos",
                                "erro": str(exc),
                                "traceback": traceback.format_exc(),
                            }
                        )

        except SiengeQuotaExceeded as exc:
            await self.db.rollback()
            logger.warning("Cota Sienge atingida no início da sincronização: %s", exc)
            status_final = StatusSincronizacao.PARCIAL
            mensagem_erro = (
                "Sincronização interrompida: limite diário de requisições da cota Sienge atingido."
            )
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Erro crítico no job de sincronização")
            status_final = StatusSincronizacao.ERRO
            mensagem_erro = str(exc)
            traceback_critico = traceback.format_exc()
        else:
            if houve_erro_cota:
                status_final = StatusSincronizacao.PARCIAL
                mensagem_erro = (
                    "Sincronização interrompida: limite diário de requisições da cota Sienge atingido."
                )
            elif houve_erro_parcial:
                status_final = StatusSincronizacao.PARCIAL
                mensagem_erro = "Sincronização concluída com falhas pontuais em obras ou fotos."
            else:
                status_final = StatusSincronizacao.SUCESSO
        finally:
            duracao_ms = max(0, int((time.perf_counter() - inicio_perf) * 1000))
            detalhes_log: dict[str, Any] = {
                "duracao_ms": duracao_ms,
                "fotos_com_erro": fotos_com_erro_total,
            }
            if erros_obras:
                detalhes_log["erros_obras"] = erros_obras
            if traceback_critico:
                detalhes_log["traceback"] = traceback_critico

            # Recarrega o LogSincronizacao de forma limpa mesmo após eventuais rollbacks
            stmt_log = select(LogSincronizacao).where(LogSincronizacao.id == log_id)
            log_persistido = (await self.db.execute(stmt_log)).scalar_one()
            log_persistido.status = status_final
            log_persistido.finalizado_em = datetime.now(UTC)
            log_persistido.diarios_novos = diarios_novos_total
            log_persistido.diarios_atualizados = diarios_atualizados_total
            log_persistido.fotos_processadas = fotos_processadas_total
            log_persistido.requisicoes_sienge = self.sienge.requisicoes
            log_persistido.mensagem_erro = mensagem_erro
            log_persistido.detalhes = detalhes_log

            await self.db.commit()
            await self.db.refresh(log_persistido)
            await self._liberar_lock(lock_key)

        return log_persistido

    # --- Sincronização de Empreendimentos e Obras -------------------------
    @staticmethod
    def _eh_empreendimento_obra_fisica(dados_emp: dict[str, Any]) -> bool:
        """Filtra centros de custo contábeis do Sienge (tipo 3/4 ou contas de inscrições/indiretos)
        para sincronizar apenas empreendimentos que representam obras físicas de engenharia."""
        tipo = str(dados_emp.get("type", "1")).strip()
        # No Sienge OpenAPI, 3 = Centro de Custo puro e 4 = Centro de Custo associado (sem engenharia)
        if tipo in ("3", "4"):
            return False

        nome = (dados_emp.get("name") or dados_emp.get("commercialName") or "").upper()
        termos_contabeis = (
            "CONSTRUTORA",
            "INDIRETO",
            "INSCRI",
            "CUSTOS ANTECIPADO",
            "CUSTOS DE OBRA",
            "DESATIVADO",
            "DESENVOLVEDOR",
            "TERRENISTA",
            "DESPESAS",
            "APORTE",
        )
        return not any(termo in nome for termo in termos_contabeis)

    async def _sincronizar_obras(
        self, obra_id_especifica: int | None = None
    ) -> list[tuple[int, int]]:
        """Sincroniza obras e devolve pares (obra.id, obra.sienge_building_id) desacoplados da sessão."""
        empreendimentos_sienge = await self.sienge.listar_empreendimentos()
        if not empreendimentos_sienge:
            return []

        dados_empresa = SiengeMapper.mapear_empresa(empreendimentos_sienge[0])
        stmt_empresa = select(Empresa).limit(1)
        empresa = (await self.db.execute(stmt_empresa)).scalar_one_or_none()
        if not empresa:
            empresa = Empresa(**dados_empresa)
            self.db.add(empresa)
            await self.db.flush()

        obras_alvos: list[tuple[int, int]] = []

        for dados_emp in empreendimentos_sienge:
            if not self._eh_empreendimento_obra_fisica(dados_emp):
                continue

            sienge_id = int(dados_emp["id"])
            campos_obra = SiengeMapper.mapear_obra(dados_emp, empresa.id)
            campos_obra["sincronizado_em"] = datetime.now(UTC)

            # Upsert atômico por sienge_building_id
            stmt_upsert = (
                pg_insert(Obra)
                .values(**campos_obra)
                .on_conflict_do_update(
                    index_elements=[Obra.sienge_building_id],
                    set_={
                        "nome": campos_obra["nome"],
                        "descricao": campos_obra["descricao"],
                        "endereco": campos_obra["endereco"],
                        "cidade": campos_obra["cidade"],
                        "uf": campos_obra["uf"],
                        "situacao": campos_obra["situacao"],
                        "dados_sienge": campos_obra["dados_sienge"],
                        "sincronizado_em": campos_obra["sincronizado_em"],
                        "atualizado_em": datetime.now(UTC),
                    },
                )
                .returning(Obra)
            )
            obra = (await self.db.execute(stmt_upsert)).scalar_one()

            if obra_id_especifica is not None and obra.id != obra_id_especifica:
                continue

            # Atualiza percentual de conclusão baseado nas medições
            try:
                percentual = await self._calcular_percentual_conclusao(sienge_id)
                if percentual is not None:
                    obra.percentual_concluido = percentual
            except SiengeQuotaExceeded:
                raise
            except (SiengeError, ValueError, TypeError, KeyError) as exc:
                logger.debug("Não foi possível obter avanço da obra %s: %s", sienge_id, exc)

            obras_alvos.append((obra.id, obra.sienge_building_id))

        await self.db.commit()
        return obras_alvos

    async def _calcular_percentual_conclusao(self, building_id: int) -> Decimal | None:
        medicoes = await self.sienge.listar_medicoes(building_id)
        if not medicoes:
            return None

        medicao_recente = sorted(
            [m for m in medicoes if m.get("consistent", True)],
            key=lambda m: m.get("measurementNumber", 0),
            reverse=True,
        )
        if not medicao_recente:
            return None

        num_medicao = medicao_recente[0]["measurementNumber"]
        unidades_construtivas: list[dict[str, Any]] = [{"id": 1}, {"id": 2}]
        try:
            detalhe = await self.sienge.obter_medicao(building_id, num_medicao)
            if detalhe.get("buildingUnits"):
                unidades_construtivas = detalhe["buildingUnits"]
        except SiengeQuotaExceeded:
            raise
        except (SiengeError, ValueError, TypeError):
            pass

        percentuais: list[float] = []
        for bu in unidades_construtivas:
            bu_id = int(bu["id"])
            try:
                itens = await self.sienge.listar_itens_medicao(building_id, num_medicao, bu_id)
                for item in itens:
                    cp = item.get("cumulativePercentage")
                    if cp is not None:
                        percentuais.append(float(cp))
            except SiengeQuotaExceeded:
                raise
            except (SiengeError, ValueError, TypeError) as exc:
                logger.debug("Falha ao ler itens de medição da unidade %s: %s", bu_id, exc)
                continue

        if percentuais:
            media = sum(percentuais) / len(percentuais)
            return Decimal(f"{media:.2f}")
        return None

    # --- Sincronização de Diários de Obra ---------------------------------
    async def _sincronizar_diarios_obra(
        self, obra_id: int, sienge_building_id: int
    ) -> tuple[int, int]:
        hoje = date.today()
        inicio = hoje - timedelta(days=self.settings.sync_lookback_days)

        resumos = await self.sienge.listar_diarios(sienge_building_id, inicio, hoje)
        if not resumos:
            return 0, 0

        novos = 0
        atualizados = 0

        mapa_tarefas = await self._obter_mapa_tarefas_planejamento(sienge_building_id)

        # Carrega a fase atual da obra e o mapa de unidades cadastradas para aplicar
        # a Política de Inversão de Risco (quarentena automática no Ponto X)
        obra_obj = (
            await self.db.execute(select(Obra).where(Obra.id == obra_id))
        ).scalar_one_or_none()
        fase_obra = obra_obj.fase_atual if obra_obj else FaseObra.ESTRUTURAL_GERAL

        unidades_obra = (
            await self.db.execute(select(Unidade).where(Unidade.obra_id == obra_id))
        ).scalars().all()
        mapa_unidades = {u.identificador: u.id for u in unidades_obra}

        # Carrega em uma única query todos os diários da obra já existentes no banco
        ids_sienge = [int(r["id"]) for r in resumos if "id" in r]
        existentes_por_sienge_id: dict[int, DiarioObra] = {}
        if ids_sienge:
            stmt_existentes = select(DiarioObra).where(
                DiarioObra.obra_id == obra_id,
                DiarioObra.sienge_diario_id.in_(ids_sienge),
            )
            for d in (await self.db.execute(stmt_existentes)).scalars().all():
                existentes_por_sienge_id[d.sienge_diario_id] = d

        for resumo in resumos:
            sienge_diario_id = int(resumo["id"])
            diario_existente = existentes_por_sienge_id.get(sienge_diario_id)

            dados_completos = await self.sienge.obter_diario(sienge_building_id, sienge_diario_id)
            campos_diario = SiengeMapper.mapear_diario(dados_completos, obra_id)
            modificado_sienge = campos_diario.get("sienge_modificado_em")

            # Se já existe e não mudou modifiedAt no Sienge, evita regravar diário, tarefas e fotos
            if (
                diario_existente
                and diario_existente.sienge_modificado_em
                and modificado_sienge
                and modificado_sienge <= diario_existente.sienge_modificado_em
            ):
                continue

            agora = datetime.now(UTC)
            campos_diario["sincronizado_em"] = agora

            stmt_upsert_diario = (
                pg_insert(DiarioObra)
                .values(**campos_diario)
                .on_conflict_do_update(
                    index_elements=[DiarioObra.obra_id, DiarioObra.sienge_diario_id],
                    set_={
                        "data": campos_diario["data"],
                        "dia_semana": campos_diario["dia_semana"],
                        "responsavel": campos_diario["responsavel"],
                        "observacoes": campos_diario["observacoes"],
                        "indice_pluviometrico": campos_diario["indice_pluviometrico"],
                        "turnos": campos_diario["turnos"],
                        "ocorrencias": campos_diario["ocorrencias"],
                        "sienge_criado_em": campos_diario["sienge_criado_em"],
                        "sienge_modificado_em": campos_diario["sienge_modificado_em"],
                        "dados_sienge": campos_diario["dados_sienge"],
                        "sincronizado_em": agora,
                        "atualizado_em": agora,
                    },
                )
                .returning(DiarioObra.id)
            )
            diario_id = (await self.db.execute(stmt_upsert_diario)).scalar_one()

            if diario_existente is None:
                novos += 1
            else:
                atualizados += 1

            await self._salvar_tarefas_diario(
                dados_completos, diario_id, mapa_tarefas, mapa_unidades=mapa_unidades
            )
            await self._salvar_metadados_fotos(
                dados_completos,
                diario_id,
                fase_obra=fase_obra,
                mapa_unidades=mapa_unidades,
            )

        await self.db.commit()
        return novos, atualizados

    async def _obter_mapa_tarefas_planejamento(self, building_id: int) -> dict[Any, str]:
        """Carrega as planilhas de planejamento (Unidades Construtivas 1 e 2 no Sienge:
        Custos Indiretos e Custos Diretos), indexando tanto por `(bu_id, task_id)` quanto por `task_id`."""
        mapa: dict[Any, str] = {}
        for bu_id in (1, 2):
            try:
                tarefas = await self.sienge.listar_tarefas_planejamento(building_id, bu_id)
                for t in tarefas:
                    t_id = t.get("id")
                    desc = t.get("description")
                    if t_id and desc:
                        tid_int = int(t_id)
                        desc_str = str(desc).strip()
                        mapa[(bu_id, tid_int)] = desc_str
                        # Prioriza Custos Diretos (bu_id=2) ou mantém caso único
                        if bu_id == 2 or tid_int not in mapa:
                            mapa[tid_int] = desc_str
            except SiengeQuotaExceeded:
                raise
            except (SiengeError, ValueError, TypeError) as exc:
                logger.debug(
                    "Não foi possível carregar planilha de planejamento (bu=%s) da obra %s: %s",
                    bu_id,
                    building_id,
                    exc,
                )
        return mapa

    async def _salvar_tarefas_diario(
        self,
        dados_diario: dict[str, Any],
        diario_id: int,
        mapa_tarefas: dict[Any, str],
        mapa_unidades: dict[str, int] | None = None,
    ) -> None:
        tarefas_dados = SiengeMapper.mapear_tarefas(
            dados_diario, diario_id, mapa_tarefas, mapa_unidades=mapa_unidades
        )
        agora = datetime.now(UTC)
        for td in tarefas_dados:
            td["sincronizado_em"] = agora
            stmt = (
                pg_insert(TarefaDiario)
                .values(**td)
                .on_conflict_do_update(
                    index_elements=[
                        TarefaDiario.diario_id,
                        TarefaDiario.tipo,
                        TarefaDiario.sienge_item_id,
                    ],
                    set_={
                        "unidade_id": td["unidade_id"],
                        "sienge_tarefa_id": td["sienge_tarefa_id"],
                        "descricao": td["descricao"],
                        "quantidade": td["quantidade"],
                        "unidade_medida": td["unidade_medida"],
                        "observacoes": td["observacoes"],
                        "dados_sienge": td["dados_sienge"],
                        "sincronizado_em": agora,
                        "atualizado_em": agora,
                    },
                )
            )
            await self.db.execute(stmt)

    async def _salvar_metadados_fotos(
        self,
        dados_diario: dict[str, Any],
        diario_id: int,
        fase_obra: FaseObra = FaseObra.ESTRUTURAL_GERAL,
        mapa_unidades: dict[str, int] | None = None,
    ) -> None:
        fotos_dados = SiengeMapper.mapear_fotos(
            dados_diario,
            diario_id,
            fase_obra=fase_obra,
            mapa_unidades=mapa_unidades,
        )
        agora = datetime.now(UTC)
        for fd in fotos_dados:
            stmt = (
                pg_insert(FotoDiario)
                .values(**fd, status=StatusFoto.PENDENTE)
                .on_conflict_do_update(
                    index_elements=[FotoDiario.diario_id, FotoDiario.sienge_attachment_number],
                    set_={
                        "nome_arquivo_original": fd["nome_arquivo_original"],
                        "descricao": fd["descricao"],
                        "local": fd["local"],
                        "ordem": fd["ordem"],
                        "atualizado_em": agora,
                    },
                )
            )
            await self.db.execute(stmt)

    # --- Pipeline de Mídia / Upload Storage ------------------------------
    async def _processar_fotos_pendentes(
        self, obra_id_especifica: int | None = None
    ) -> tuple[int, int, bool]:
        stmt = (
            select(FotoDiario, DiarioObra, Obra)
            .join(DiarioObra, FotoDiario.diario_id == DiarioObra.id)
            .join(Obra, DiarioObra.obra_id == Obra.id)
            .where(FotoDiario.status == StatusFoto.PENDENTE)
            .order_by(FotoDiario.criado_em.asc())
            .limit(self.settings.sync_fotos_por_execucao)
        )
        if obra_id_especifica is not None:
            stmt = stmt.where(Obra.id == obra_id_especifica)

        resultados = (await self.db.execute(stmt)).all()
        processadas = 0
        com_erro = 0
        cota_atingida = False

        for foto, diario, obra in resultados:
            try:
                # 1. Download único do Sienge
                bytes_originais = await self.sienge.baixar_anexo(
                    obra.sienge_building_id,
                    diario.sienge_diario_id,
                    foto.sienge_attachment_number,
                )

                # 2. Compressão e conversão para WebP via Pillow em thread separada (não bloqueia Event Loop)
                imagem_webp = await self.media.processar_foto_async(bytes_originais)

                # 3. Upload assíncrono para Object Storage
                chave_storage = (
                    f"obras/{obra.sienge_building_id}/diarios/{diario.sienge_diario_id}"
                    f"_{foto.sienge_attachment_number}.webp"
                )
                url_publica = await self.storage.salvar(
                    chave=chave_storage,
                    conteudo=imagem_webp.conteudo,
                    content_type="image/webp",
                )

                # 4. Atualização cadastral no banco
                foto.storage_key = chave_storage
                foto.url = url_publica
                foto.largura = imagem_webp.largura
                foto.altura = imagem_webp.altura
                foto.tamanho_bytes = imagem_webp.tamanho_bytes
                foto.status = StatusFoto.PROCESSADA
                foto.erro = None
                processadas += 1

                if not obra.imagem_capa_url:
                    obra.imagem_capa_url = url_publica

                await self.db.commit()

            except SiengeQuotaExceeded as exc:
                # Cota esgotou: preserva as fotos já salvas e interrompe o lote imediatamente
                logger.warning("Cota Sienge atingida ao baixar foto: %s", exc)
                await self.db.commit()
                cota_atingida = True
                break
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Erro ao processar foto %s do diário %s: %s",
                    foto.sienge_attachment_number,
                    diario.sienge_diario_id,
                    exc,
                )
                foto.status = StatusFoto.ERRO
                foto.erro = str(exc)[:500]
                com_erro += 1
                await self.db.commit()

        return processadas, com_erro, cota_atingida
