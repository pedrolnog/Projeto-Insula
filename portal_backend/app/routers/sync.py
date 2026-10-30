from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import exigir_admin_ou_api_key
from app.models.enums import OrigemSincronizacao, StatusSincronizacao
from app.models.log_sincronizacao import LogSincronizacao
from app.services.seed_service import garantir_usuarios_iniciais
from app.services.sync_service import SyncAlreadyRunningError, SyncService

router = APIRouter(prefix="/sync", tags=["Sincronização Sienge"])


class LogSincronizacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origem: OrigemSincronizacao
    status: StatusSincronizacao
    obra_id: int | None
    iniciado_em: datetime
    finalizado_em: datetime | None
    duracao_ms: int | None
    diarios_novos: int
    diarios_atualizados: int
    fotos_processadas: int
    requisicoes_sienge: int
    mensagem_erro: str | None
    detalhes: dict[str, Any] | None = None


@router.post(
    "",
    response_model=LogSincronizacaoResponse,
    summary="Dispara sincronização manual com o Sienge",
    dependencies=[Depends(exigir_admin_ou_api_key)],
)
async def disparar_sincronizacao(
    obra_id: int | None = Query(
        None, description="ID interno da obra específica (ou null para todas)"
    ),
    db: AsyncSession = Depends(get_db),
) -> LogSincronizacaoResponse:
    """Dispara imediatamente o processo de ingestão e pipeline de fotos."""
    sync_service = SyncService(db=db)
    try:
        log = await sync_service.sincronizar_tudo(
            origem=OrigemSincronizacao.MANUAL,
            obra_id_especifica=obra_id,
        )
    except SyncAlreadyRunningError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    await garantir_usuarios_iniciais(db)
    return LogSincronizacaoResponse.model_validate(log)


@router.get(
    "/logs",
    response_model=list[LogSincronizacaoResponse],
    summary="Lista o histórico de sincronizações",
    dependencies=[Depends(exigir_admin_ou_api_key)],
)
async def listar_logs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LogSincronizacaoResponse]:
    stmt = select(LogSincronizacao).order_by(desc(LogSincronizacao.iniciado_em)).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()
    return [LogSincronizacaoResponse.model_validate(log) for log in logs]
