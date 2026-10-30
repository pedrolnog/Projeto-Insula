"""Serviço de seed idempotente para ambiente de desenvolvimento e homologação.

Garante a existência de:
1. Um usuário Administrador (`CPF: 00000000000`, `senha: admin123`).
2. Um usuário Condômino de demonstração (`CPF: 11122233344`, `senha: benedetto123`)
   vinculado à Obra 101 e às suas próprias unidades (`Apto 302` e `Apto 501`),
   além de uma unidade de outro condômino (`Apto 404`) para demonstrar e testar
   o isolamento estrito entre unidades no Ponto X (Fase de Reformas).
"""
import logging
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import gerar_hash_senha, mascarar_cpf
from app.models.diario import DiarioObra
from app.models.enums import FaseObra, PerfilUsuario, StatusFoto, StatusReformaUnidade, TipoTarefa
from app.models.foto import FotoDiario
from app.models.obra import Obra
from app.models.tarefa import TarefaDiario
from app.models.unidade import Unidade, usuarios_unidades
from app.models.usuario import Usuario, usuarios_obras

logger = logging.getLogger(__name__)


async def garantir_usuarios_iniciais(db: AsyncSession) -> None:
    """Cria ou atualiza os usuários e unidades de demonstração APENAS se SIENGE_USE_MOCK=true."""
    settings = get_settings()
    if not settings.sienge_use_mock:
        logger.info(
            "garantir_usuarios_iniciais ignorado: SIENGE_USE_MOCK=false. "
            "Credenciais e dados de demonstração não são criados em ambiente com dados reais."
        )
        return

    # 1. Administrador padrão
    stmt_admin = select(Usuario).where(Usuario.cpf == "00000000000")
    admin = (await db.execute(stmt_admin)).scalar_one_or_none()
    if not admin:
        admin = Usuario(
            cpf="00000000000",
            nome="Administrador Benedetto",
            email="admin@benedetto.com.br",
            telefone="11999990000",
            senha_hash=gerar_hash_senha("admin123"),
            perfil=PerfilUsuario.ADMIN,
            ativo=True,
        )
        db.add(admin)
        await db.flush()
        logger.info("Usuário Admin inicial criado (CPF: %s).", mascarar_cpf(admin.cpf))

    # 2. Condômino de demonstração (João Silva - possui 2 unidades: Apto 302 e Apto 501)
    stmt_condomino = select(Usuario).where(Usuario.cpf == "11122233344")
    condomino = (await db.execute(stmt_condomino)).scalar_one_or_none()
    if not condomino:
        condomino = Usuario(
            cpf="11122233344",
            nome="João Silva (Condômino)",
            email="joao.silva@email.com",
            telefone="11988887777",
            senha_hash=gerar_hash_senha("benedetto123"),
            perfil=PerfilUsuario.CONDOMINO,
            ativo=True,
        )
        db.add(condomino)
        await db.flush()
        logger.info("Usuário Condômino inicial criado (CPF: %s).", mascarar_cpf(condomino.cpf))

    # 3. Segundo Condômino na mesma obra (Carlos Mendes - dono do Apto 404, invisível para João)
    stmt_vizinho = select(Usuario).where(Usuario.cpf == "22233344455")
    vizinho = (await db.execute(stmt_vizinho)).scalar_one_or_none()
    if not vizinho:
        vizinho = Usuario(
            cpf="22233344455",
            nome="Carlos Mendes (Vizinho Apto 404)",
            email="carlos.mendes@email.com",
            telefone="11977776666",
            senha_hash=gerar_hash_senha("benedetto123"),
            perfil=PerfilUsuario.CONDOMINO,
            ativo=True,
        )
        db.add(vizinho)
        await db.flush()

    # 4. Localiza a Obra 101 (ou primeira obra existente)
    stmt_obra = select(Obra).where(Obra.sienge_building_id == 101)
    obra_demo = (await db.execute(stmt_obra)).scalar_one_or_none()
    if not obra_demo:
        obra_demo = (
            await db.execute(select(Obra).order_by(Obra.id.asc()).limit(1))
        ).scalar_one_or_none()

    if obra_demo:
        stmt_vinculo_cond = (
            pg_insert(usuarios_obras)
            .values(usuario_id=condomino.id, obra_id=obra_demo.id)
            .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
        )
        await db.execute(stmt_vinculo_cond)

        stmt_vinculo_viz = (
            pg_insert(usuarios_obras)
            .values(usuario_id=vizinho.id, obra_id=obra_demo.id)
            .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
        )
        await db.execute(stmt_vinculo_viz)

    # Só injeta unidades/fotos/tarefas fictícias de demonstração se for a Obra 101 (Mock)
    if obra_demo and obra_demo.sienge_building_id == 101:
        # Configura a Obra Mock 101 no Ponto X (REFORMAS_UNIDADES) para demonstrar o foco na unidade
        obra_demo.fase_atual = FaseObra.REFORMAS_UNIDADES

        # Cria unidades de demonstração de forma idempotente
        unidades_spec = [
            {
                "identificador": "Apto 302 - Torre A",
                "sienge_unit_id": 101302,
                "status_reforma": StatusReformaUnidade.EM_ANDAMENTO,
                "percentual_reforma": Decimal("68.50"),
                "observacoes_reforma": (
                    "Porcelanato 90x90 instalado na sala e varanda gourmet. "
                    "Forro de gesso concluído e bancadas de quartzo em montagem."
                ),
                "dono_id": condomino.id,
            },
            {
                "identificador": "Apto 501 - Torre A",
                "sienge_unit_id": 101501,
                "status_reforma": StatusReformaUnidade.CONCLUIDA,
                "percentual_reforma": Decimal("100.00"),
                "observacoes_reforma": (
                    "Acabamentos internos, pintura acrílica premium, louças e metais "
                    "100% finalizados e aprovados na vistoria de qualidade."
                ),
                "dono_id": condomino.id,
            },
            {
                "identificador": "Apto 404 - Torre A",
                "sienge_unit_id": 101404,
                "status_reforma": StatusReformaUnidade.EM_ANDAMENTO,
                "percentual_reforma": Decimal("35.00"),
                "observacoes_reforma": (
                    "Impermeabilização dos banheiros e contrapiso acústico do Apto 404."
                ),
                "dono_id": vizinho.id,
            },
        ]

        unidades_criadas: dict[str, Unidade] = {}
        for spec in unidades_spec:
            stmt_u = (
                pg_insert(Unidade)
                .values(
                    obra_id=obra_demo.id,
                    identificador=spec["identificador"],
                    sienge_unit_id=spec["sienge_unit_id"],
                    status_reforma=spec["status_reforma"],
                    percentual_reforma=spec["percentual_reforma"],
                    observacoes_reforma=spec["observacoes_reforma"],
                )
                .on_conflict_do_update(
                    index_elements=[Unidade.obra_id, Unidade.identificador],
                    set_={
                        "status_reforma": spec["status_reforma"],
                        "percentual_reforma": spec["percentual_reforma"],
                        "observacoes_reforma": spec["observacoes_reforma"],
                    },
                )
                .returning(Unidade)
            )
            unidade_obj = (await db.execute(stmt_u)).scalar_one()
            unidades_criadas[spec["identificador"]] = unidade_obj

            stmt_vu = (
                pg_insert(usuarios_unidades)
                .values(usuario_id=spec["dono_id"], unidade_id=unidade_obj.id)
                .on_conflict_do_nothing(index_elements=["usuario_id", "unidade_id"])
            )
            await db.execute(stmt_vu)

        # Vincula fotos e tarefas exclusivas às unidades no último diário da Obra 101
        stmt_ultimo_diario = (
            select(DiarioObra)
            .where(DiarioObra.obra_id == obra_demo.id)
            .order_by(desc(DiarioObra.data))
            .limit(1)
        )
        ultimo_diario = (await db.execute(stmt_ultimo_diario)).scalar_one_or_none()
        if ultimo_diario:
            # Pega uma URL WebP já processada da obra para reutilizar como imagem de exemplo
            stmt_foto_ref = (
                select(FotoDiario.url)
                .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
                .where(
                    DiarioObra.obra_id == obra_demo.id,
                    FotoDiario.status == StatusFoto.PROCESSADA,
                    FotoDiario.url.is_not(None),
                )
                .limit(1)
            )
            url_exemplo = (
                await db.execute(stmt_foto_ref)
            ).scalar_one_or_none() or "/media/obras/101/diarios/101020_1.webp"

            u_302 = unidades_criadas["Apto 302 - Torre A"]
            u_501 = unidades_criadas["Apto 501 - Torre A"]
            u_404 = unidades_criadas["Apto 404 - Torre A"]

            fotos_unidades = [
                {
                    "sienge_attachment_number": 93021,
                    "unidade_id": u_302.id,
                    "descricao": "Assentamento de porcelanato 90x90 no living e varanda gourmet",
                    "local": "Apto 302 - Living / Varanda",
                    "ordem": 1,
                },
                {
                    "sienge_attachment_number": 93022,
                    "unidade_id": u_302.id,
                    "descricao": "Instalação de bancada em quartzo branco e revestimento da suíte",
                    "local": "Apto 302 - Suíte Master",
                    "ordem": 2,
                },
                {
                    "sienge_attachment_number": 95011,
                    "unidade_id": u_501.id,
                    "descricao": "Vistoria final aprovada: pintura, luminárias e metais instalados",
                    "local": "Apto 501 - Geral",
                    "ordem": 1,
                },
                {
                    "sienge_attachment_number": 94041,
                    "unidade_id": u_404.id,
                    "publicado": True,
                    "descricao": "Foto privada do Apto 404 (exclusiva do condômino Carlos)",
                    "local": "Apto 404 - Banheiro",
                    "ordem": 1,
                },
                {
                    "sienge_attachment_number": 99901,
                    "unidade_id": None,
                    "publicado": False,  # Retida automaticamente em QUARENTENA!
                    "descricao": "Vistoria de bancada de mármore e tubulação de água quente (enviada sem unidade no Sienge)",
                    "local": "Interior de Apartamento (Sem Tag)",
                    "ordem": 99,
                },
            ]
            for f_spec in fotos_unidades:
                publicado_val = f_spec.get("publicado", True)
                stmt_f = (
                    pg_insert(FotoDiario)
                    .values(
                        diario_id=ultimo_diario.id,
                        sienge_attachment_number=f_spec["sienge_attachment_number"],
                        unidade_id=f_spec["unidade_id"],
                        publicado=publicado_val,
                        nome_arquivo_original=f"unidade_{f_spec['sienge_attachment_number']}.webp",
                        descricao=f_spec["descricao"],
                        local=f_spec["local"],
                        ordem=f_spec["ordem"],
                        status=StatusFoto.PROCESSADA,
                        url=url_exemplo,
                        largura=1280,
                        altura=960,
                    )
                    .on_conflict_do_update(
                        index_elements=[FotoDiario.diario_id, FotoDiario.sienge_attachment_number],
                        set_={
                            "unidade_id": f_spec["unidade_id"],
                            "publicado": publicado_val,
                            "descricao": f_spec["descricao"],
                            "local": f_spec["local"],
                            "status": StatusFoto.PROCESSADA,
                            "url": url_exemplo,
                        },
                    )
                )
                await db.execute(stmt_f)

            tarefas_unidades = [
                {
                    "sienge_item_id": 83021,
                    "unidade_id": u_302.id,
                    "tipo": TipoTarefa.PLANEJADA,
                    "descricao": "Assentamento de piso porcelanato retificado 90x90cm",
                    "quantidade": Decimal("64.50"),
                    "unidade_medida": "m²",
                    "observacoes": "Concluído na sala e varanda do Apto 302",
                },
                {
                    "sienge_item_id": 83022,
                    "unidade_id": u_302.id,
                    "tipo": TipoTarefa.PLANEJADA,
                    "descricao": "Forro de gesso acartonado tabicado e sanca iluminada",
                    "quantidade": Decimal("58.00"),
                    "unidade_medida": "m²",
                    "observacoes": "Pronto para emassamento e pintura",
                },
                {
                    "sienge_item_id": 85011,
                    "unidade_id": u_501.id,
                    "tipo": TipoTarefa.PLANEJADA,
                    "descricao": "Pintura final acrílica premium e instalação de metais",
                    "quantidade": Decimal("100.00"),
                    "unidade_medida": "%",
                    "observacoes": "Unidade Apto 501 liberada para entrega",
                },
                {
                    "sienge_item_id": 84041,
                    "unidade_id": u_404.id,
                    "tipo": TipoTarefa.AVULSA,
                    "descricao": "Serviço exclusivo interno do Apto 404",
                    "quantidade": Decimal("1.00"),
                    "unidade_medida": "un",
                    "observacoes": "Privado do Apto 404",
                },
            ]
            for t_spec in tarefas_unidades:
                stmt_t = (
                    pg_insert(TarefaDiario)
                    .values(
                        diario_id=ultimo_diario.id,
                        unidade_id=t_spec["unidade_id"],
                        tipo=t_spec["tipo"],
                        sienge_item_id=t_spec["sienge_item_id"],
                        descricao=t_spec["descricao"],
                        quantidade=t_spec["quantidade"],
                        unidade_medida=t_spec["unidade_medida"],
                        observacoes=t_spec["observacoes"],
                    )
                    .on_conflict_do_update(
                        index_elements=[
                            TarefaDiario.diario_id,
                            TarefaDiario.tipo,
                            TarefaDiario.sienge_item_id,
                        ],
                        set_={
                            "unidade_id": t_spec["unidade_id"],
                            "descricao": t_spec["descricao"],
                            "quantidade": t_spec["quantidade"],
                            "unidade_medida": t_spec["unidade_medida"],
                            "observacoes": t_spec["observacoes"],
                        },
                    )
                )
                await db.execute(stmt_t)

    await db.commit()
