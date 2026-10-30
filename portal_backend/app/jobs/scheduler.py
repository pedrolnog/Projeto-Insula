"""Agendamento periódico de sincronização com o Sienge via APScheduler."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.enums import OrigemSincronizacao
from app.services.sync_service import SyncAlreadyRunningError, SyncService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 3600,
    }
)


async def executar_job_sincronizacao() -> None:
    """Executado pelo cron do APScheduler 2x/dia (ou horas configuradas)."""
    logger.info("Iniciando rotina agendada de sincronização com Sienge (CRON)...")
    async with AsyncSessionLocal() as session:
        sync_service = SyncService(db=session)
        try:
            log = await sync_service.sincronizar_tudo(origem=OrigemSincronizacao.CRON)
            logger.info(
                "Rotina agendada finalizada com status %s (%dms): %d diários novos, %d atualizados, %d fotos.",
                log.status,
                log.duracao_ms or 0,
                log.diarios_novos,
                log.diarios_atualizados,
                log.fotos_processadas,
            )
        except SyncAlreadyRunningError:
            logger.warning(
                "Execução agendada (CRON) ignorada: já existe outra sincronização em andamento."
            )


def iniciar_scheduler() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("APScheduler desabilitado via configuração (SCHEDULER_ENABLED=false).")
        return

    horas = settings.sync_cron_hours.strip()
    trigger = CronTrigger(hour=horas, minute=0, timezone=settings.sync_timezone)

    scheduler.configure(timezone=settings.sync_timezone)
    scheduler.add_job(
        executar_job_sincronizacao,
        trigger=trigger,
        id="sincronizacao_sienge_cron",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
        name="Sincronização Periódica Sienge",
    )
    if not scheduler.running:
        scheduler.start()
    logger.info(
        "APScheduler iniciado (%s). Execuções programadas para as horas: [%s]",
        settings.sync_timezone,
        horas,
    )


def parar_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler encerrado.")
