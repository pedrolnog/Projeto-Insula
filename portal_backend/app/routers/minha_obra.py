"""Rotas do Portal do Condômino (`/api/v1/minha-obra`).

Regras de ouro de Segurança, Isolamento e Alta Performance (750+ Condôminos Simultâneos):
1. Zero Sienge Direct: Nenhuma rota deste módulo realiza chamadas ao ERP Sienge.
2. Isolamento por Obra (`usuarios_obras`): o condômino só acessa obras vinculadas ao seu CPF.
3. Isolamento por Unidade (`usuarios_unidades`):
   - Na Visão Geral do Edifício (`/minha-obra` e `/minha-obra/diarios`), o carregamento
     ansioso (`selectinload` com `and_`) filtra diretamente no SQL `unidade_id IS NULL` e
     `publicado = true`, impedindo tráfego desnecessário na rede e vazamento entre unidades.
   - Na Visão por Unidade (`/minha-obra/unidades/{unidade_id}`), a validação de propriedade,
     dados da obra e contadores são resolvidos com queries enxutas e paginação obrigatória
     (`pagina_fotos`, `tamanho_pagina_fotos`, `limite_tarefas`).
"""
import math
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.core.security import obter_usuario_atual
from app.models.diario import DiarioObra
from app.models.enums import PerfilUsuario, StatusFoto
from app.models.foto import FotoDiario
from app.models.obra import Obra
from app.models.tarefa import TarefaDiario
from app.models.unidade import Unidade, usuarios_unidades
from app.models.usuario import Usuario, usuarios_obras
from app.schemas.obra import (
    DiarioObraSchema,
    DiariosPaginadosResponse,
    FotoDiarioSchema,
    MinhaObraResponse,
    MinhaUnidadeDetalheResponse,
    ObraVinculadaResumoSchema,
    TarefaDiarioSchema,
    UnidadeVinculadaResumoSchema,
)

router = APIRouter(prefix="/minha-obra", tags=["Portal do Condômino"])


async def _resolver_obras_do_usuario(
    db: AsyncSession,
    usuario: Usuario,
) -> list[Obra]:
    """Retorna todas as obras visíveis no portal às quais o usuário tem acesso."""
    if usuario.perfil == PerfilUsuario.ADMIN:
        stmt = (
            select(Obra)
            .where(Obra.visivel_portal.is_(True))
            .order_by(Obra.id.asc())
        )
    else:
        stmt = (
            select(Obra)
            .join(usuarios_obras, usuarios_obras.c.obra_id == Obra.id)
            .where(
                usuarios_obras.c.usuario_id == usuario.id,
                Obra.visivel_portal.is_(True),
            )
            .order_by(Obra.id.asc())
        )
    return list((await db.execute(stmt)).scalars().all())


async def _selecionar_obra_autorizada(
    db: AsyncSession,
    usuario: Usuario,
    obra_id: int | None,
) -> tuple[Obra, list[Obra]]:
    """Valida o multi-tenancy de obra e retorna `(obra_selecionada, todas_obras_vinculadas)`."""
    obras_vinculadas = await _resolver_obras_do_usuario(db, usuario)
    if not obras_vinculadas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma obra ativa está vinculada ao seu cadastro.",
        )

    if obra_id is None:
        return obras_vinculadas[0], obras_vinculadas

    for obra in obras_vinculadas:
        if obra.id == obra_id:
            return obra, obras_vinculadas

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Você não possui permissão para visualizar os dados desta obra.",
    )


async def _resolver_unidades_do_usuario_na_obra(
    db: AsyncSession,
    usuario: Usuario,
    obra_id: int,
) -> list[UnidadeVinculadaResumoSchema]:
    """Retorna as unidades do usuário na obra junto com `total_fotos` em UMA ÚNICA query SQL."""
    subq_fotos = (
        select(
            FotoDiario.unidade_id.label("unidade_id"),
            func.count(FotoDiario.id).label("total_fotos"),
        )
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .where(
            DiarioObra.obra_id == obra_id,
            DiarioObra.publicado.is_(True),
            FotoDiario.status == StatusFoto.PROCESSADA,
            FotoDiario.publicado.is_(True),
            FotoDiario.url.is_not(None),
            FotoDiario.unidade_id.is_not(None),
        )
        .group_by(FotoDiario.unidade_id)
        .subquery()
    )

    stmt = (
        select(Unidade, func.coalesce(subq_fotos.c.total_fotos, 0))
        .outerjoin(subq_fotos, subq_fotos.c.unidade_id == Unidade.id)
        .where(Unidade.obra_id == obra_id)
        .order_by(Unidade.identificador.asc())
    )

    if usuario.perfil != PerfilUsuario.ADMIN:
        stmt = stmt.join(
            usuarios_unidades,
            and_(
                usuarios_unidades.c.unidade_id == Unidade.id,
                usuarios_unidades.c.usuario_id == usuario.id,
            ),
        )

    linhas = (await db.execute(stmt)).all()
    return [
        UnidadeVinculadaResumoSchema(
            id=u.id,
            obra_id=u.obra_id,
            identificador=u.identificador,
            status_reforma=u.status_reforma,
            percentual_reforma=u.percentual_reforma,
            observacoes_reforma=u.observacoes_reforma,
            total_fotos=int(qtd_fotos or 0),
        )
        for u, qtd_fotos in linhas
    ]


def _serializar_diario_geral(diario: DiarioObra) -> DiarioObraSchema:
    """Converte `DiarioObra` em schema garantindo apenas itens gerais (`unidade_id is None`)."""
    fotos_gerais_prontas = [
        FotoDiarioSchema.model_validate(f)
        for f in (diario.fotos or [])
        if f.status == StatusFoto.PROCESSADA
        and f.publicado
        and f.url
        and f.unidade_id is None
    ]
    tarefas_gerais = [
        TarefaDiarioSchema.model_validate(t)
        for t in (diario.tarefas or [])
        if t.unidade_id is None
    ]
    return DiarioObraSchema(
        id=diario.id,
        obra_id=diario.obra_id,
        data=diario.data,
        dia_semana=diario.dia_semana,
        responsavel=diario.responsavel,
        observacoes=diario.observacoes,
        indice_pluviometrico=diario.indice_pluviometrico,
        turnos=diario.turnos or [],
        ocorrencias=diario.ocorrencias or [],
        tarefas=tarefas_gerais,
        fotos=fotos_gerais_prontas,
    )


@router.get(
    "",
    response_model=MinhaObraResponse,
    summary="Retorna os dados gerais da obra, fase atual (Ponto X) e unidades vinculadas em 2 queries otimizadas",
)
async def obter_minha_obra(
    obra_id: int | None = Query(
        None,
        description="ID da obra desejada (opcional; padrão é a primeira obra vinculada ao CPF)",
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> MinhaObraResponse:
    """Resolve indicadores de diários, fotos gerais e unidades do condômino sem N+1 queries."""
    obra, obras_vinculadas = await _selecionar_obra_autorizada(db, usuario_atual, obra_id)

    # Query única consolidada para total_diarios, ultimo_diario_data e total_fotos gerais
    stmt_metricas = select(
        func.count(DiarioObra.id).label("total_diarios"),
        func.max(DiarioObra.data).label("ultimo_diario_data"),
        select(func.count(FotoDiario.id))
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .where(
            DiarioObra.obra_id == obra.id,
            DiarioObra.publicado.is_(True),
            FotoDiario.status == StatusFoto.PROCESSADA,
            FotoDiario.publicado.is_(True),
            FotoDiario.url.is_not(None),
            FotoDiario.unidade_id.is_(None),
        )
        .scalar_subquery()
        .label("total_fotos"),
    ).where(
        DiarioObra.obra_id == obra.id,
        DiarioObra.publicado.is_(True),
    )
    total_diarios, ultimo_diario_data, total_fotos = (
        await db.execute(stmt_metricas)
    ).one()

    unidades_do_condomino = await _resolver_unidades_do_usuario_na_obra(
        db, usuario_atual, obra.id
    )

    return MinhaObraResponse(
        id=obra.id,
        nome=obra.nome,
        descricao=obra.descricao,
        endereco=obra.endereco,
        cidade=obra.cidade,
        uf=obra.uf,
        situacao=obra.situacao,
        fase_atual=obra.fase_atual,
        percentual_concluido=obra.percentual_concluido,
        data_inicio=obra.data_inicio,
        data_previsao_entrega=obra.data_previsao_entrega,
        imagem_capa_url=obra.imagem_capa_url,
        sincronizado_em=obra.sincronizado_em,
        total_diarios=int(total_diarios or 0),
        total_fotos=int(total_fotos or 0),
        ultimo_diario_data=ultimo_diario_data,
        obras_vinculadas=[
            ObraVinculadaResumoSchema.model_validate(o) for o in obras_vinculadas
        ],
        unidades_vinculadas=unidades_do_condomino,
    )


@router.get(
    "/unidades",
    response_model=list[UnidadeVinculadaResumoSchema],
    summary="Lista exclusivamente as unidades autônomas vinculadas ao condômino na obra",
)
async def listar_minhas_unidades(
    obra_id: int | None = Query(
        None,
        description="ID da obra desejada (opcional; padrão é a primeira obra vinculada)",
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> list[UnidadeVinculadaResumoSchema]:
    """Retorna apenas os apartamentos/unidades que pertencem ao condômino autenticado."""
    obra, _ = await _selecionar_obra_autorizada(db, usuario_atual, obra_id)
    return await _resolver_unidades_do_usuario_na_obra(db, usuario_atual, obra.id)


@router.get(
    "/unidades/{unidade_id}",
    response_model=MinhaUnidadeDetalheResponse,
    summary="Retorna o status da reforma, tarefas e fotos paginadas de uma unidade do condômino",
)
async def obter_detalhe_minha_unidade(
    unidade_id: int,
    pagina_fotos: int = Query(1, ge=1, description="Página da galeria de fotos da unidade"),
    tamanho_pagina_fotos: int = Query(
        20, ge=1, le=50, description="Quantidade de fotos por página na unidade"
    ),
    limite_tarefas: int = Query(
        50, ge=1, le=100, description="Limite máximo de tarefas retornadas da unidade"
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> MinhaUnidadeDetalheResponse:
    """Valida propriedade da unidade e retorna fotos/tarefas paginadas (nunca executa SELECT * sem limite)."""
    stmt_unidade = (
        select(Unidade)
        .options(joinedload(Unidade.obra))
        .where(Unidade.id == unidade_id)
    )
    unidade = (await db.execute(stmt_unidade)).scalar_one_or_none()

    if not unidade or not unidade.obra.visivel_portal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unidade não encontrada.",
        )

    # Validação estrita de propriedade da unidade (Multi-Tenancy no nível de Unidade)
    if usuario_atual.perfil != PerfilUsuario.ADMIN:
        stmt_vinculo = select(usuarios_unidades.c.unidade_id).where(
            usuarios_unidades.c.usuario_id == usuario_atual.id,
            usuarios_unidades.c.unidade_id == unidade_id,
        )
        possui_acesso = (await db.execute(stmt_vinculo)).scalar_one_or_none()
        if not possui_acesso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não possui permissão para visualizar os dados desta unidade.",
            )

    filtros_fotos = [
        FotoDiario.unidade_id == unidade.id,
        DiarioObra.publicado.is_(True),
        FotoDiario.status == StatusFoto.PROCESSADA,
        FotoDiario.publicado.is_(True),
        FotoDiario.url.is_not(None),
    ]

    stmt_total_fotos = (
        select(func.count(FotoDiario.id))
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .where(*filtros_fotos)
    )
    total_fotos = int((await db.execute(stmt_total_fotos)).scalar_one() or 0)
    total_paginas_fotos = (
        max(1, math.ceil(total_fotos / tamanho_pagina_fotos))
        if total_fotos > 0
        else 1
    )

    offset_fotos = (pagina_fotos - 1) * tamanho_pagina_fotos
    stmt_fotos = (
        select(FotoDiario)
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .where(*filtros_fotos)
        .order_by(desc(DiarioObra.data), FotoDiario.ordem.asc())
        .offset(offset_fotos)
        .limit(tamanho_pagina_fotos)
    )
    fotos = (await db.execute(stmt_fotos)).scalars().all()

    stmt_tarefas = (
        select(TarefaDiario)
        .join(DiarioObra, DiarioObra.id == TarefaDiario.diario_id)
        .where(
            TarefaDiario.unidade_id == unidade.id,
            DiarioObra.publicado.is_(True),
        )
        .order_by(desc(DiarioObra.data), TarefaDiario.id.asc())
        .limit(limite_tarefas)
    )
    tarefas = (await db.execute(stmt_tarefas)).scalars().all()

    return MinhaUnidadeDetalheResponse(
        id=unidade.id,
        obra_id=unidade.obra_id,
        obra_nome=unidade.obra.nome,
        identificador=unidade.identificador,
        status_reforma=unidade.status_reforma,
        percentual_reforma=unidade.percentual_reforma,
        observacoes_reforma=unidade.observacoes_reforma,
        atualizado_em=unidade.atualizado_em,
        total_fotos=total_fotos,
        pagina_fotos=pagina_fotos,
        tamanho_pagina_fotos=tamanho_pagina_fotos,
        total_paginas_fotos=total_paginas_fotos,
        fotos=[FotoDiarioSchema.model_validate(f) for f in fotos],
        tarefas=[TarefaDiarioSchema.model_validate(t) for t in tarefas],
    )


@router.get(
    "/diarios",
    response_model=DiariosPaginadosResponse,
    summary="Lista o feed paginado de diários GERAIS do edifício (eager loading filtrado no SQL)",
)
async def listar_diarios_minha_obra(
    obra_id: int | None = Query(
        None,
        description="ID da obra desejada (opcional; padrão é a primeira obra vinculada)",
    ),
    pagina: int = Query(1, ge=1, description="Número da página (1-indexed)"),
    tamanho_pagina: int = Query(10, ge=1, le=50, description="Itens por página"),
    data_inicio: date | None = Query(
        None, description="Filtro opcional de data inicial (YYYY-MM-DD)"
    ),
    data_fim: date | None = Query(
        None, description="Filtro opcional de data final (YYYY-MM-DD)"
    ),
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> DiariosPaginadosResponse:
    """Retorna diários gerais com `selectinload` filtrado no PostgreSQL (`unidade_id IS NULL`)."""
    obra, _ = await _selecionar_obra_autorizada(db, usuario_atual, obra_id)

    filtros = [
        DiarioObra.obra_id == obra.id,
        DiarioObra.publicado.is_(True),
    ]
    if data_inicio is not None:
        filtros.append(DiarioObra.data >= data_inicio)
    if data_fim is not None:
        filtros.append(DiarioObra.data <= data_fim)

    stmt_total = select(func.count(DiarioObra.id)).where(*filtros)
    total = int((await db.execute(stmt_total)).scalar_one() or 0)
    total_paginas = max(1, math.ceil(total / tamanho_pagina)) if total > 0 else 0

    offset = (pagina - 1) * tamanho_pagina
    stmt_itens = (
        select(DiarioObra)
        .where(*filtros)
        .options(
            selectinload(
                DiarioObra.tarefas.and_(TarefaDiario.unidade_id.is_(None))
            ),
            selectinload(
                DiarioObra.fotos.and_(
                    FotoDiario.unidade_id.is_(None),
                    FotoDiario.status == StatusFoto.PROCESSADA,
                    FotoDiario.publicado.is_(True),
                    FotoDiario.url.is_not(None),
                )
            ),
        )
        .order_by(desc(DiarioObra.data), desc(DiarioObra.id))
        .offset(offset)
        .limit(tamanho_pagina)
    )
    diarios = (await db.execute(stmt_itens)).scalars().all()

    return DiariosPaginadosResponse(
        obra_id=obra.id,
        obra_nome=obra.nome,
        total=total,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
        total_paginas=total_paginas,
        itens=[_serializar_diario_geral(d) for d in diarios],
    )


@router.get(
    "/diarios/{diario_id}",
    response_model=DiarioObraSchema,
    summary="Retorna os detalhes gerais de um diário de obra específico",
)
async def obter_detalhe_diario(
    diario_id: int,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> DiarioObraSchema:
    """Busca um diário específico filtrando itens de unidades diretamente no `selectinload`."""
    obras_vinculadas = await _resolver_obras_do_usuario(db, usuario_atual)
    ids_obras_permitidas = {o.id for o in obras_vinculadas}

    stmt = (
        select(DiarioObra)
        .where(
            DiarioObra.id == diario_id,
            DiarioObra.publicado.is_(True),
        )
        .options(
            selectinload(
                DiarioObra.tarefas.and_(TarefaDiario.unidade_id.is_(None))
            ),
            selectinload(
                DiarioObra.fotos.and_(
                    FotoDiario.unidade_id.is_(None),
                    FotoDiario.status == StatusFoto.PROCESSADA,
                    FotoDiario.publicado.is_(True),
                    FotoDiario.url.is_not(None),
                )
            ),
        )
    )
    diario = (await db.execute(stmt)).scalar_one_or_none()

    if not diario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diário de obra não encontrado.",
        )

    if diario.obra_id not in ids_obras_permitidas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não possui permissão para visualizar este diário de obra.",
        )

    return _serializar_diario_geral(diario)
