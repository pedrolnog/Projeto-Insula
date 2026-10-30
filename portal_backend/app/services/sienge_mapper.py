"""Utilitários de conversão e normalização dos dados vindos da API do Sienge."""
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.enums import FaseObra, TipoTarefa

Json = dict[str, Any]


def parse_date(valor: Any) -> date | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        return date.fromisoformat(valor[:10])
    except (ValueError, TypeError):
        return None


def parse_datetime(valor: Any) -> datetime | None:
    if not valor or not isinstance(valor, str):
        return None
    try:
        # Trata formatos ISO do Sienge (ex: 2024-07-15T18:00:00 ou com microssegundos/Z)
        limpo = valor.replace("Z", "+00:00")
        dt = datetime.fromisoformat(limpo)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


def parse_decimal(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


class SiengeMapper:
    """Mapeia dicionários da API do Sienge para estruturas dos models SQLAlchemy."""

    @staticmethod
    def mapear_empresa(dados: Json) -> dict[str, Any]:
        return {
            "nome": dados.get("companyName") or "Empresa Padrão",
            "cnpj": (dados.get("cnpj") or "").replace(".", "").replace("/", "").replace("-", "").strip() or None,
            "ativo": True,
        }

    @staticmethod
    def mapear_obra(dados: Json, empresa_id: int) -> dict[str, Any]:
        nome_bruto = (dados.get("commercialName") or "").strip() or (dados.get("name") or "").strip()
        endereco = (dados.get("adress") or "").strip() or None
        addr_details = dados.get("addressDetails") or {}
        cidade = (addr_details.get("city") or "").strip() or None
        uf = (addr_details.get("state") or "").strip()[:2] or None

        return {
            "empresa_id": empresa_id,
            "sienge_building_id": int(dados["id"]),
            "sienge_enterprise_id": int(dados["id"]),
            "nome": nome_bruto or f"Obra {dados['id']}",
            "descricao": (dados.get("enterpriseObservation") or "").strip() or None,
            "endereco": endereco,
            "cidade": cidade,
            "uf": uf,
            "situacao": str(dados.get("type")) if dados.get("type") is not None else None,
            "dados_sienge": dados,
        }

    @staticmethod
    def mapear_diario(dados: Json, obra_id: int) -> dict[str, Any]:
        turnos_normalizados: list[dict[str, Any]] = []
        for s in dados.get("shifts") or []:
            if isinstance(s, dict):
                turnos_normalizados.append({
                    **s,
                    "descricao": s.get("descricao") or s.get("description"),
                    "inicio": s.get("inicio") or s.get("startTime"),
                    "fim": s.get("fim") or s.get("finishTime"),
                    "clima": s.get("clima") or s.get("weatherCondition"),
                })

        ocorrencias_normalizadas: list[dict[str, Any]] = []
        for ev in dados.get("events") or []:
            if isinstance(ev, dict):
                ocorrencias_normalizadas.append({
                    **ev,
                    "descricao": ev.get("descricao") or ev.get("description"),
                    "tipo": ev.get("tipo") or ev.get("eventTypeDescription") or "Nota de Canteiro",
                })

        return {
            "obra_id": obra_id,
            "sienge_diario_id": int(dados["id"]),
            "data": parse_date(dados.get("date")) or date.today(),
            "dia_semana": dados.get("weekDay"),
            "responsavel": dados.get("responsibleId"),
            "observacoes": dados.get("notes"),
            "indice_pluviometrico": parse_decimal(dados.get("rainfallIndex")),
            "turnos": turnos_normalizados,
            "ocorrencias": ocorrencias_normalizadas,
            "sienge_criado_em": parse_datetime(dados.get("createdAt")),
            "sienge_modificado_em": parse_datetime(dados.get("modifiedAt")),
            "dados_sienge": dados,
        }

    @staticmethod
    def mapear_tarefas(
        dados_diario: Json,
        diario_id: int,
        mapa_planejamento: dict[Any, str] | None = None,
        mapa_unidades: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        tarefas: list[dict[str, Any]] = []
        mapa_planejamento = mapa_planejamento or {}

        # 1. Tarefas planejadas (plannedTasks)
        for item in dados_diario.get("plannedTasks") or []:
            task_id = item.get("taskId")
            bu_id = item.get("buildingUnitId")
            descricao = None
            if task_id is not None:
                if bu_id is not None:
                    descricao = mapa_planejamento.get((int(bu_id), int(task_id)))
                if not descricao:
                    descricao = mapa_planejamento.get(int(task_id))

            notas = item.get("notes")
            unidade_id = SiengeMapper.resolver_unidade_por_texto(
                notas, descricao, mapa_unidades
            )
            tarefas.append({
                "diario_id": diario_id,
                "unidade_id": unidade_id,
                "tipo": TipoTarefa.PLANEJADA,
                "sienge_item_id": int(item["id"]),
                "sienge_tarefa_id": int(task_id) if task_id else None,
                "descricao": descricao or f"Tarefa Planejada #{task_id}",
                "quantidade": parse_decimal(item.get("quantity")),
                "unidade_medida": item.get("unitOfMeasure"),
                "observacoes": notas,
                "dados_sienge": item,
            })

        # 2. Tarefas avulsas (detachedTasks)
        for item in dados_diario.get("detachedTasks") or []:
            desc_avulsa = item.get("description") or f"Tarefa Avulsa #{item['id']}"
            notas = item.get("notes")
            unidade_id = SiengeMapper.resolver_unidade_por_texto(
                notas, desc_avulsa, mapa_unidades
            )
            tarefas.append({
                "diario_id": diario_id,
                "unidade_id": unidade_id,
                "tipo": TipoTarefa.AVULSA,
                "sienge_item_id": int(item["id"]),
                "sienge_tarefa_id": None,
                "descricao": desc_avulsa,
                "quantidade": parse_decimal(item.get("quantity")),
                "unidade_medida": item.get("unitOfMeasure"),
                "observacoes": notas,
                "dados_sienge": item,
            })

        return tarefas

    @staticmethod
    def resolver_unidade_por_texto(
        texto_local: str | None,
        texto_descricao: str | None,
        mapa_unidades: dict[str, int] | None,
    ) -> int | None:
        """Tenta identificar a qual unidade um item pertence analisando `location` e `description`.

        `mapa_unidades` associa o identificador da unidade (ex.: "Apto 302 - Torre A") ao seu `id`.
        """
        if not mapa_unidades:
            return None

        texto_combinado = f"{texto_local or ''} {texto_descricao or ''}".lower()
        if not texto_combinado.strip():
            return None

        for identificador, unidade_id in mapa_unidades.items():
            ident_lower = identificador.lower().strip()
            if ident_lower and ident_lower in texto_combinado:
                return unidade_id

            # Extrai números de 2 a 4 dígitos do identificador (ex.: "302" de "Apto 302 - Torre A")
            numeros = re.findall(r"\b\d{2,4}\b", ident_lower)
            for num in numeros:
                padrao = rf"\b(?:apto\.?|apartamento|unid\.?|unidade)\s*0*{re.escape(num)}\b"
                if re.search(padrao, texto_combinado):
                    return unidade_id

        return None

    @staticmethod
    def mapear_fotos(
        dados_diario: Json,
        diario_id: int,
        fase_obra: FaseObra = FaseObra.ESTRUTURAL_GERAL,
        mapa_unidades: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Mapeia anexos fotográficos aplicando a Política de Inversão de Risco no Ponto X.

        - Se a foto tiver correspondência clara com uma unidade cadastrada, recebe `unidade_id` e `publicado=True`
          (visível apenas ao dono daquela unidade).
        - Se NÃO tiver unidade identificada:
          * Na fase `ESTRUTURAL_GERAL`: assume público do edifício (`unidade_id=None`, `publicado=True`).
          * Nas fases `REFORMAS_UNIDADES` ou `ENTREGA` (Ponto X): entra automaticamente em QUARENTENA
            (`unidade_id=None`, `publicado=False`) para curadoria rápida do engenheiro/admin, evitando
            qualquer risco de vazar foto interna de apartamento sem tag no feed coletivo.
        """
        fotos: list[dict[str, Any]] = []
        em_fase_sensivel = fase_obra in (FaseObra.REFORMAS_UNIDADES, FaseObra.ENTREGA)

        for idx, anexo in enumerate(dados_diario.get("attachments") or []):
            local_str = anexo.get("location")
            desc_str = anexo.get("description")
            unidade_id = SiengeMapper.resolver_unidade_por_texto(
                local_str, desc_str, mapa_unidades
            )
            if unidade_id is not None:
                publicado = True
            else:
                publicado = not em_fase_sensivel

            fotos.append({
                "diario_id": diario_id,
                "unidade_id": unidade_id,
                "publicado": publicado,
                "sienge_attachment_number": int(anexo.get("attachmentNumber") or (idx + 1)),
                "nome_arquivo_original": anexo.get("name"),
                "descricao": desc_str,
                "local": local_str,
                "ordem": idx,
            })
        return fotos
