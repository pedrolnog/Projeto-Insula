"""Utilitários de autenticação JWT, hash de senha (bcrypt off-thread), rate limit e dependências de segurança."""
import asyncio
import re
import secrets
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.enums import PerfilUsuario
from app.models.usuario import Usuario

bearer_scheme = HTTPBearer(auto_error=False)

# Controle de Rate Limit Sliding Window em memória por IP para proteger o endpoint de Login
_historico_tentativas_por_ip: dict[str, deque[float]] = {}


def normalizar_cpf(cpf: str) -> str:
    """Remove pontuação e espaços do CPF, mantendo apenas os dígitos."""
    return re.sub(r"\D", "", cpf or "")


def mascarar_cpf(cpf: str) -> str:
    """Retorna CPF mascarado no formato ***.456.789-** para conformidade com a LGPD."""
    digitos = normalizar_cpf(cpf)
    if len(digitos) != 11:
        return "***.***.***-**"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


def gerar_hash_senha(senha: str) -> str:
    """Gera hash bcrypt seguro para armazenamento no banco (uso síncrono / scripts)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode("utf-8"), salt).decode("utf-8")


async def gerar_hash_senha_async(senha: str) -> str:
    """Gera hash bcrypt fora do Event Loop principal para não travar rotas concorrentes."""
    return await asyncio.to_thread(gerar_hash_senha, senha)


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Compara senha em texto plano com o hash bcrypt armazenado (síncrono)."""
    try:
        return bcrypt.checkpw(senha_plana.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


async def verificar_senha_async(senha_plana: str, senha_hash: str) -> bool:
    """Executa a verificação CPU-bound do bcrypt em thread separada (`asyncio.to_thread`).

    Fundamental para cenários de pico (ex.: 300+ condôminos logando após notificação de novo diário),
    impedindo que os ~250ms do bcrypt bloqueiem o Event Loop assíncrono do FastAPI.
    """
    return await asyncio.to_thread(verificar_senha, senha_plana, senha_hash)


def verificar_rate_limit_login(request: Request) -> None:
    """Limita a taxa de tentativas de login por IP (Sliding Window) prevenindo abuso de CPU e brute-force."""
    settings = get_settings()
    ip_cliente = (
        request.headers.get("cf-connecting-ip")
        or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    agora = time.monotonic()
    janela = float(settings.login_rate_limit_window_seconds)
    limite = settings.login_rate_limit_max_requests

    fila = _historico_tentativas_por_ip.get(ip_cliente)
    if fila is None:
        fila = deque()
        _historico_tentativas_por_ip[ip_cliente] = fila

    while fila and (agora - fila[0]) > janela:
        fila.popleft()

    if len(fila) >= limite:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login em curto intervalo. Aguarde 1 minuto e tente novamente.",
            headers={"Retry-After": str(settings.login_rate_limit_window_seconds)},
        )

    fila.append(agora)


def criar_access_token(usuario: Usuario) -> tuple[str, int]:
    """Cria um token JWT assinado contendo sub (id), cpf e perfil do usuário."""
    settings = get_settings()
    expira_em_segundos = settings.jwt_expire_minutes * 60
    agora = datetime.now(UTC)
    expiracao = agora + timedelta(seconds=expira_em_segundos)
    payload: dict[str, Any] = {
        "sub": str(usuario.id),
        "cpf": usuario.cpf,
        "perfil": str(usuario.perfil.value),
        "iat": int(agora.timestamp()),
        "exp": int(expiracao.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expira_em_segundos


def decodificar_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Dependência FastAPI que autentica o usuário via Bearer JWT e verifica se está ativo."""
    if not credenciais or not credenciais.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais de autenticação não fornecidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_access_token(credenciais.credentials)
    sub = payload.get("sub")
    if not sub or not str(sub).isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(Usuario).where(Usuario.id == int(sub))
    usuario = (await db.execute(stmt)).scalar_one_or_none()

    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inexistente ou inativo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


async def exigir_admin(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
) -> Usuario:
    """Exige obrigatoriamente um usuário autenticado via Bearer JWT com perfil ADMIN.

    Nunca permite acesso anônimo, mesmo em ambiente de desenvolvimento sem ADMIN_API_KEY.
    """
    if usuario_atual.perfil != PerfilUsuario.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return usuario_atual


async def exigir_admin_ou_api_key(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permite acesso a rotas de sincronização via JWT de Admin ou X-Admin-Key (comparação em tempo constante)."""
    settings = get_settings()

    if credenciais and credenciais.credentials:
        usuario = await obter_usuario_atual(credenciais=credenciais, db=db)
        if usuario.perfil == PerfilUsuario.ADMIN:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )

    if settings.admin_api_key:
        if x_admin_key and secrets.compare_digest(x_admin_key, settings.admin_api_key):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação de administrador necessária (Bearer JWT ou X-Admin-Key).",
        )
