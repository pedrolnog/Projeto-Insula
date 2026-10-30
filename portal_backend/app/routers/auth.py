"""Rotas de autenticação por CPF e sessão do usuário (`/api/v1/auth`)."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    criar_access_token,
    mascarar_cpf,
    obter_usuario_atual,
    verificar_rate_limit_login,
    verificar_senha_async,
)
from app.models.usuario import Usuario
from app.schemas.auth import (
    AceiteTermoPrivacidadeResponse,
    LoginRequest,
    TokenResponse,
    UsuarioResumoSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica condômino ou admin via CPF e senha (não-bloqueante + rate limit)",
    dependencies=[Depends(verificar_rate_limit_login)],
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Valida CPF e senha sem bloquear o Event Loop (`asyncio.to_thread`) e retorna um JWT."""
    stmt = select(Usuario).where(Usuario.cpf == payload.cpf)
    usuario = (await db.execute(stmt)).scalar_one_or_none()

    if not usuario or not await verificar_senha_async(payload.senha, usuario.senha_hash):
        logger.warning(
            "Tentativa de login falha para o CPF %s (senha inválida ou usuário inexistente)",
            mascarar_cpf(payload.cpf),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.ativo:
        logger.warning(
            "Tentativa de login bloqueada para conta inativa (CPF %s, ID=%s)",
            mascarar_cpf(usuario.cpf),
            usuario.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está temporariamente inativa. Entre em contato com a administração.",
        )

    usuario.ultimo_login_em = datetime.now(UTC)
    await db.commit()

    logger.info(
        "Login realizado com sucesso para o usuário ID=%s (CPF %s, perfil=%s)",
        usuario.id,
        mascarar_cpf(usuario.cpf),
        usuario.perfil.value,
    )

    token, expira_em = criar_access_token(usuario)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expira_em,
        usuario=UsuarioResumoSchema.model_validate(usuario),
    )


@router.get(
    "/me",
    response_model=UsuarioResumoSchema,
    summary="Retorna os dados do usuário autenticado",
)
async def obter_perfil_atual(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
) -> UsuarioResumoSchema:
    """Retorna o resumo cadastral do condômino ou administrador logado."""
    return UsuarioResumoSchema.model_validate(usuario_atual)


@router.post(
    "/aceitar-termo-privacidade",
    response_model=AceiteTermoPrivacidadeResponse,
    summary="Registra o aceite expresso dos Termos de Uso e Política de Privacidade (LGPD)",
)
async def aceitar_termo_privacidade(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: AsyncSession = Depends(get_db),
) -> AceiteTermoPrivacidadeResponse:
    """Registra a data e hora do consentimento/ciência dos termos pelo condômino."""
    agora = datetime.now(UTC)
    usuario_atual.termo_privacidade_aceito_em = agora
    await db.commit()

    logger.info(
        "Termo de privacidade aceito para o usuário ID=%s (CPF %s)",
        usuario_atual.id,
        mascarar_cpf(usuario_atual.cpf),
    )

    return AceiteTermoPrivacidadeResponse(
        mensagem="Termo de Uso e Política de Privacidade aceito com sucesso.",
        termo_privacidade_aceito_em=agora,
    )
