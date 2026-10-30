"""Rotas Administrativas de Curadoria / Moderação de Fotos em Quarentena e Gestão do Ponto X (`/api/v1/admin`).

Quando uma obra está na fase `REFORMAS_UNIDADES` ou `ENTREGA` (Ponto X), fotos vindas do Sienge
sem identificação clara de unidade entram automaticamente em quarentena (`publicado=False`).
Este módulo permite ao engenheiro/administrador:
1. Listar as fotos pendentes de classificação (`GET /api/v1/admin/fotos-quarentena`).
2. Aprovar uma foto como Geral do Edifício (`unidade_id=None, publicado=True`) ou vinculá-la
   a uma Unidade específica (`unidade_id=X, publicado=True`) com 1 clique (`PATCH /api/v1/admin/fotos/{foto_id}/classificar`).
3. Alternar a fase atual da obra (`PATCH /api/v1/admin/obras/{obra_id}/fase`).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import exigir_admin, gerar_hash_senha_async, normalizar_cpf
from app.models.diario import DiarioObra
from app.models.enums import PerfilUsuario, StatusFoto
from app.models.foto import FotoDiario
from app.models.obra import Obra
from app.models.unidade import Unidade, usuarios_unidades
from app.models.usuario import Usuario, usuarios_obras
from app.schemas.auth import (
    AtualizarUsuarioRequest,
    CriarUsuarioRequest,
    UsuarioAdminSchema,
)
from app.schemas.obra import (
    AlterarFaseObraRequest,
    AtualizarObraAdminRequest,
    ClassificarFotoRequest,
    FotoQuarentenaAdminSchema,
)

router = APIRouter(
    prefix="/admin",
    tags=["Administração & Curadoria (Ponto X)"],
    dependencies=[Depends(exigir_admin)],
)


@router.get(
    "/fotos-quarentena",
    response_model=list[FotoQuarentenaAdminSchema],
    summary="Lista fotos retidas em quarentena aguardando classificação do engenheiro/admin",
)
async def listar_fotos_quarentena(
    obra_id: int | None = Query(None, description="Filtra por ID da obra"),
    apenas_pendentes: bool = Query(
        True, description="Se True, retorna apenas fotos com publicado=False"
    ),
    pagina: int = Query(1, ge=1, description="Número da página (1-indexed)"),
    tamanho_pagina: int = Query(50, ge=1, le=100, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
) -> list[FotoQuarentenaAdminSchema]:
    offset = (pagina - 1) * tamanho_pagina
    stmt = (
        select(FotoDiario, DiarioObra, Obra)
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .join(Obra, Obra.id == DiarioObra.obra_id)
        .where(
            FotoDiario.status == StatusFoto.PROCESSADA,
            FotoDiario.url.is_not(None),
        )
        .order_by(desc(DiarioObra.data), FotoDiario.id.desc())
        .offset(offset)
        .limit(tamanho_pagina)
    )
    if obra_id is not None:
        stmt = stmt.where(Obra.id == obra_id)
    if apenas_pendentes:
        stmt = stmt.where(FotoDiario.publicado.is_(False))

    linhas = (await db.execute(stmt)).all()
    return [
        FotoQuarentenaAdminSchema(
            id=foto.id,
            diario_id=diario.id,
            obra_id=obra.id,
            obra_nome=obra.nome,
            data_diario=diario.data,
            url=foto.url or "",
            descricao=foto.descricao,
            local=foto.local,
            unidade_id=foto.unidade_id,
            publicado=foto.publicado,
        )
        for foto, diario, obra in linhas
    ]


@router.patch(
    "/fotos/{foto_id}/classificar",
    response_model=FotoQuarentenaAdminSchema,
    summary="Classifica uma foto em quarentena (Edifício Geral ou Unidade específica) e aprova publicação",
)
async def classificar_foto(
    foto_id: int,
    payload: ClassificarFotoRequest,
    db: AsyncSession = Depends(get_db),
) -> FotoQuarentenaAdminSchema:
    stmt = (
        select(FotoDiario, DiarioObra, Obra)
        .join(DiarioObra, DiarioObra.id == FotoDiario.diario_id)
        .join(Obra, Obra.id == DiarioObra.obra_id)
        .where(FotoDiario.id == foto_id)
    )
    linha = (await db.execute(stmt)).one_or_none()
    if not linha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto não encontrada.",
        )

    foto, diario, obra = linha

    # Se o admin vinculou a uma unidade, valida se a unidade pertence à mesma obra da foto
    if payload.unidade_id is not None:
        unidade = (
            await db.execute(
                select(Unidade).where(
                    Unidade.id == payload.unidade_id,
                    Unidade.obra_id == obra.id,
                )
            )
        ).scalar_one_or_none()
        if not unidade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A unidade informada não pertence a esta obra.",
            )
        if not payload.local:
            foto.local = unidade.identificador

    foto.unidade_id = payload.unidade_id
    foto.publicado = payload.publicado
    if payload.descricao is not None:
        foto.descricao = payload.descricao
    if payload.local is not None:
        foto.local = payload.local

    await db.commit()
    await db.refresh(foto)

    return FotoQuarentenaAdminSchema(
        id=foto.id,
        diario_id=diario.id,
        obra_id=obra.id,
        obra_nome=obra.nome,
        data_diario=diario.data,
        url=foto.url or "",
        descricao=foto.descricao,
        local=foto.local,
        unidade_id=foto.unidade_id,
        publicado=foto.publicado,
    )


@router.patch(
    "/obras/{obra_id}/fase",
    summary="Altera a fase atual da obra (ex.: virar a chave para o Ponto X: reformas_unidades)",
)
async def alterar_fase_obra(
    obra_id: int,
    payload: AlterarFaseObraRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    obra = (await db.execute(select(Obra).where(Obra.id == obra_id))).scalar_one_or_none()
    if not obra:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obra não encontrada.",
        )
    obra.fase_atual = payload.fase_atual
    await db.commit()
    return {
        "obra_id": obra.id,
        "nome": obra.nome,
        "fase_atual": obra.fase_atual.value,
    }


@router.patch(
    "/obras/{obra_id}",
    summary="Atualiza dados da obra (percentual de evolução física geral, fase atual, situação e previsão de entrega)",
)
async def atualizar_obra(
    obra_id: int,
    payload: AtualizarObraAdminRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    obra = (await db.execute(select(Obra).where(Obra.id == obra_id))).scalar_one_or_none()
    if not obra:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Obra não encontrada.",
        )

    if payload.fase_atual is not None:
        obra.fase_atual = payload.fase_atual

    if payload.percentual_concluido is not None:
        if payload.percentual_concluido < 0 or payload.percentual_concluido > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O percentual de conclusão deve estar entre 0.00% e 100.00%.",
            )
        obra.percentual_concluido = payload.percentual_concluido

    if payload.situacao is not None:
        obra.situacao = payload.situacao

    if payload.data_previsao_entrega is not None:
        obra.data_previsao_entrega = payload.data_previsao_entrega

    await db.commit()
    await db.refresh(obra)

    return {
        "obra_id": obra.id,
        "nome": obra.nome,
        "fase_atual": obra.fase_atual.value,
        "percentual_concluido": float(obra.percentual_concluido) if obra.percentual_concluido is not None else 0.0,
        "situacao": obra.situacao,
        "data_previsao_entrega": obra.data_previsao_entrega.isoformat() if obra.data_previsao_entrega else None,
    }


# --- Gestão Completa de Perfis de Usuários (CRUD Otimizado & Blindado) ----


async def _validar_obras_e_unidades_em_lote(
    db: AsyncSession, obras_ids: list[int], unidades_ids: list[int]
) -> None:
    """Valida a existência de todas as obras e unidades informadas em no máximo 2 queries (O(1))."""
    if obras_ids:
        encontradas = set(
            (await db.execute(select(Obra.id).where(Obra.id.in_(obras_ids)))).scalars().all()
        )
        faltantes = [oid for oid in obras_ids if oid not in encontradas]
        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Obra(s) não encontrada(s): {faltantes}.",
            )

    if unidades_ids:
        encontradas_u = set(
            (await db.execute(select(Unidade.id).where(Unidade.id.in_(unidades_ids))))
            .scalars()
            .all()
        )
        faltantes_u = [uid for uid in unidades_ids if uid not in encontradas_u]
        if faltantes_u:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unidade(s) não encontrada(s): {faltantes_u}.",
            )


async def _montar_usuarios_admin_em_lote(
    db: AsyncSession, usuarios: list[Usuario]
) -> list[UsuarioAdminSchema]:
    """Resolve `obras_vinculadas_ids` e `unidades_vinculadas_ids` para todos os usuários em 2 queries em lote,
    eliminando completamente o problema de N+1 queries."""
    if not usuarios:
        return []

    ids_usuarios = [u.id for u in usuarios]
    obras_por_usuario: dict[int, list[int]] = {uid: [] for uid in ids_usuarios}
    unidades_por_usuario: dict[int, list[int]] = {uid: [] for uid in ids_usuarios}

    linhas_obras = (
        await db.execute(
            select(usuarios_obras.c.usuario_id, usuarios_obras.c.obra_id)
            .where(usuarios_obras.c.usuario_id.in_(ids_usuarios))
            .order_by(usuarios_obras.c.obra_id.asc())
        )
    ).all()
    for u_id, o_id in linhas_obras:
        obras_por_usuario[u_id].append(o_id)

    linhas_unidades = (
        await db.execute(
            select(usuarios_unidades.c.usuario_id, usuarios_unidades.c.unidade_id)
            .where(usuarios_unidades.c.usuario_id.in_(ids_usuarios))
            .order_by(usuarios_unidades.c.unidade_id.asc())
        )
    ).all()
    for u_id, un_id in linhas_unidades:
        unidades_por_usuario[u_id].append(un_id)

    return [
        UsuarioAdminSchema(
            id=u.id,
            cpf=u.cpf,
            nome=u.nome,
            email=u.email,
            telefone=u.telefone,
            perfil=u.perfil,
            ativo=u.ativo,
            obras_vinculadas_ids=obras_por_usuario[u.id],
            unidades_vinculadas_ids=unidades_por_usuario[u.id],
        )
        for u in usuarios
    ]


@router.get(
    "/usuarios",
    response_model=list[UsuarioAdminSchema],
    summary="Lista perfis de usuários com paginação, filtros e vínculos resolvidos em lote (Zero N+1)",
)
async def listar_usuarios(
    perfil: PerfilUsuario | None = Query(None, description="Filtra por perfil (admin ou condomino)"),
    busca: str | None = Query(None, description="Filtra por nome ou CPF parcial"),
    pagina: int = Query(1, ge=1, description="Página (1-indexed)"),
    tamanho_pagina: int = Query(50, ge=1, le=200, description="Itens por página"),
    db: AsyncSession = Depends(get_db),
) -> list[UsuarioAdminSchema]:
    offset = (pagina - 1) * tamanho_pagina
    stmt = select(Usuario).order_by(Usuario.id.asc()).offset(offset).limit(tamanho_pagina)

    if perfil is not None:
        stmt = stmt.where(Usuario.perfil == perfil)

    if busca and busca.strip():
        termo = busca.strip()
        cpf_digitos = normalizar_cpf(termo)
        condicoes = [Usuario.nome.ilike(f"%{termo}%")]
        if cpf_digitos:
            condicoes.append(Usuario.cpf.like(f"%{cpf_digitos}%"))
        stmt = stmt.where(or_(*condicoes))

    usuarios = list((await db.execute(stmt)).scalars().all())
    return await _montar_usuarios_admin_em_lote(db, usuarios)


@router.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminSchema,
    summary="Visualiza os detalhes completos e vínculos de um perfil específico",
)
async def obter_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
) -> UsuarioAdminSchema:
    usuario = (
        await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    ).scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )
    montados = await _montar_usuarios_admin_em_lote(db, [usuario])
    return montados[0]


@router.post(
    "/usuarios",
    response_model=UsuarioAdminSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo perfil (Administrador ou Condômino) com Bcrypt off-thread e bulk insert",
)
async def criar_usuario(
    payload: CriarUsuarioRequest,
    db: AsyncSession = Depends(get_db),
) -> UsuarioAdminSchema:
    # 1. Verifica unicidade de CPF
    existente = (
        await db.execute(select(Usuario.id).where(Usuario.cpf == payload.cpf))
    ).scalar_one_or_none()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um usuário cadastrado com o CPF {payload.cpf}.",
        )

    # 2. Valida obras e unidades em lote único (O(1))
    await _validar_obras_e_unidades_em_lote(db, payload.obras_ids, payload.unidades_ids)

    # 3. Gera hash da senha fora do Event Loop (não bloqueia requisições concorrentes)
    senha_hash = await gerar_hash_senha_async(payload.senha)

    usuario = Usuario(
        cpf=payload.cpf,
        nome=payload.nome.strip(),
        email=payload.email.strip() if payload.email else None,
        telefone=payload.telefone.strip() if payload.telefone else None,
        senha_hash=senha_hash,
        perfil=payload.perfil,
        ativo=True,
    )
    db.add(usuario)
    await db.flush()

    # 4. Bulk insert atômico dos vínculos
    if payload.obras_ids:
        await db.execute(
            pg_insert(usuarios_obras)
            .values([{"usuario_id": usuario.id, "obra_id": oid} for oid in payload.obras_ids])
            .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
        )

    if payload.unidades_ids:
        await db.execute(
            pg_insert(usuarios_unidades)
            .values([{"usuario_id": usuario.id, "unidade_id": uid} for uid in payload.unidades_ids])
            .on_conflict_do_nothing(index_elements=["usuario_id", "unidade_id"])
        )

    await db.commit()
    await db.refresh(usuario)

    return UsuarioAdminSchema(
        id=usuario.id,
        cpf=usuario.cpf,
        nome=usuario.nome,
        email=usuario.email,
        telefone=usuario.telefone,
        perfil=usuario.perfil,
        ativo=usuario.ativo,
        obras_vinculadas_ids=payload.obras_ids,
        unidades_vinculadas_ids=payload.unidades_ids,
    )


@router.patch(
    "/usuarios/{usuario_id}",
    response_model=UsuarioAdminSchema,
    summary="Atualiza dados cadastrais, senha, perfil, status ativo ou vínculos de um usuário",
)
async def atualizar_usuario(
    usuario_id: int,
    payload: AtualizarUsuarioRequest,
    admin_atual: Usuario = Depends(exigir_admin),
    db: AsyncSession = Depends(get_db),
) -> UsuarioAdminSchema:
    usuario = (
        await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    ).scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Trava Anti-Lockout: impede que o admin desative ou rebaixe a própria conta
    if usuario.id == admin_atual.id:
        if payload.ativo is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode desativar a sua própria conta de administrador.",
            )
        if payload.perfil is not None and payload.perfil != PerfilUsuario.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode remover o perfil de administrador da sua própria conta.",
            )

    if payload.cpf is not None and payload.cpf != usuario.cpf:
        conflito_cpf = (
            await db.execute(
                select(Usuario.id).where(
                    Usuario.cpf == payload.cpf,
                    Usuario.id != usuario.id,
                )
            )
        ).scalar_one_or_none()
        if conflito_cpf:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"O CPF {payload.cpf} já pertence a outro usuário.",
            )
        usuario.cpf = payload.cpf

    if payload.nome is not None:
        usuario.nome = payload.nome.strip()
    if "email" in payload.model_fields_set:
        usuario.email = payload.email.strip() if payload.email else None
    if "telefone" in payload.model_fields_set:
        usuario.telefone = payload.telefone.strip() if payload.telefone else None
    if payload.perfil is not None:
        usuario.perfil = payload.perfil
    if payload.ativo is not None:
        usuario.ativo = payload.ativo
    if payload.senha is not None:
        usuario.senha_hash = await gerar_hash_senha_async(payload.senha)

    # Atualização de vínculos de obras e unidades (se enviados no payload)
    await _validar_obras_e_unidades_em_lote(
        db,
        payload.obras_ids or [],
        payload.unidades_ids or [],
    )

    if payload.obras_ids is not None:
        await db.execute(
            delete(usuarios_obras).where(usuarios_obras.c.usuario_id == usuario.id)
        )
        if payload.obras_ids:
            await db.execute(
                pg_insert(usuarios_obras)
                .values([{"usuario_id": usuario.id, "obra_id": oid} for oid in payload.obras_ids])
                .on_conflict_do_nothing(index_elements=["usuario_id", "obra_id"])
            )

    if payload.unidades_ids is not None:
        await db.execute(
            delete(usuarios_unidades).where(usuarios_unidades.c.usuario_id == usuario.id)
        )
        if payload.unidades_ids:
            await db.execute(
                pg_insert(usuarios_unidades)
                .values(
                    [{"usuario_id": usuario.id, "unidade_id": uid} for uid in payload.unidades_ids]
                )
                .on_conflict_do_nothing(index_elements=["usuario_id", "unidade_id"])
            )

    await db.commit()
    await db.refresh(usuario)

    montados = await _montar_usuarios_admin_em_lote(db, [usuario])
    return montados[0]


@router.delete(
    "/usuarios/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um perfil de usuário e todos os seus vínculos (com trava anti auto-exclusão)",
)
async def apagar_usuario(
    usuario_id: int,
    admin_atual: Usuario = Depends(exigir_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if usuario_id == admin_atual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operação bloqueada: você não pode apagar a sua própria conta de administrador.",
        )

    usuario = (
        await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    ).scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    # Impede apagar o último administrador ativo do sistema
    if usuario.perfil == PerfilUsuario.ADMIN:
        qtd_admins = (
            await db.execute(
                select(func.count())
                .select_from(Usuario)
                .where(Usuario.perfil == PerfilUsuario.ADMIN, Usuario.ativo.is_(True))
            )
        ).scalar_one()
        if qtd_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operação bloqueada: não é permitido remover o único administrador ativo.",
            )

    await db.delete(usuario)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
