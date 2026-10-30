import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.sienge import HttpSiengeClient, MockSiengeClient, SiengeQuotaExceeded
from app.core.config import Settings
from app.models.diario import DiarioObra
from app.models.enums import OrigemSincronizacao, StatusFoto, StatusSincronizacao
from app.models.foto import FotoDiario
from app.models.obra import Obra
from app.models.tarefa import TarefaDiario
from app.services.media_service import MediaService
from app.services.seed_service import garantir_usuarios_iniciais
from app.services.sync_service import SyncAlreadyRunningError, SyncService, _process_lock


@pytest.mark.asyncio
async def test_media_service_conversao_webp_async():
    mock_client = MockSiengeClient()
    bytes_originais = await mock_client.baixar_anexo(101, 1, 1)
    assert len(bytes_originais) > 0

    media_svc = MediaService()
    processada = await media_svc.processar_foto_async(bytes_originais)

    assert processada.content_type == "image/webp"
    assert processada.largura > 0
    assert processada.altura > 0
    assert len(processada.conteudo) > 0
    assert processada.conteudo[:4] == b"RIFF"
    assert processada.conteudo[8:12] == b"WEBP"


@pytest.mark.asyncio
async def test_http_sienge_client_rate_limit_429_e_quota_exceeded():
    chamadas = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(
            200,
            json={
                "resultSetMetadata": {"count": 1, "limit": 200, "offset": 0},
                "results": [{"id": 101, "name": "Obra Teste"}],
            },
        )

    settings = Settings(
        sienge_use_mock=False,
        sienge_base_url="https://api.sienge.com.br/sub/public/api/v1",
        sienge_user="u",
        sienge_password="p",
        sienge_max_retries=2,
        sienge_backoff_seconds=1,
        sienge_max_wait_seconds=5,
    )
    async with HttpSiengeClient(settings, transport=httpx.MockTransport(handler)) as client:
        res = await client.listar_empreendimentos()
        assert len(res) == 1
        assert client.requisicoes == 2

    # Se Retry-After exceder sienge_max_wait_seconds, lança SiengeQuotaExceeded imediatamente
    def handler_cota_esgotada(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "3600"})

    async with HttpSiengeClient(
        settings, transport=httpx.MockTransport(handler_cota_esgotada)
    ) as client:
        with pytest.raises(SiengeQuotaExceeded):
            await client.listar_empreendimentos()
        assert client.requisicoes == 1


@pytest.mark.asyncio
async def test_sync_service_bloqueio_concorrencia(db_session: AsyncSession):
    sync_svc = SyncService(db=db_session)
    await _process_lock.acquire()
    try:
        with pytest.raises(SyncAlreadyRunningError):
            await sync_svc.sincronizar_tudo(origem=OrigemSincronizacao.CRON)
    finally:
        _process_lock.release()


@pytest.mark.asyncio
async def test_sync_service_execucao_completa_e_idempotencia(db_session: AsyncSession):
    await db_session.execute(
        text(
            "TRUNCATE TABLE logs_sincronizacao, fotos_diario, tarefas_diario, diarios_obra, obras, empresas CASCADE"
        )
    )
    await db_session.commit()

    sync_svc = SyncService(db=db_session)

    # 1. Primeira Execução da Ingestão
    log_1 = await sync_svc.sincronizar_tudo(origem=OrigemSincronizacao.MANUAL)

    assert log_1.status == StatusSincronizacao.SUCESSO
    assert log_1.diarios_novos > 0
    assert log_1.fotos_processadas > 0
    assert log_1.requisicoes_sienge > 0
    assert log_1.duracao_ms is not None and log_1.duracao_ms >= 0
    assert log_1.detalhes is not None and "duracao_ms" in log_1.detalhes

    stmt_obras = select(func.count()).select_from(Obra)
    qtd_obras_1 = (await db_session.execute(stmt_obras)).scalar_one()
    assert qtd_obras_1 >= 2

    stmt_diarios = select(func.count()).select_from(DiarioObra)
    qtd_diarios_1 = (await db_session.execute(stmt_diarios)).scalar_one()
    assert qtd_diarios_1 > 0

    stmt_tarefas = select(func.count()).select_from(TarefaDiario)
    qtd_tarefas_1 = (await db_session.execute(stmt_tarefas)).scalar_one()
    assert qtd_tarefas_1 > 0

    stmt_fotos = select(FotoDiario).where(FotoDiario.status == StatusFoto.PROCESSADA)
    fotos_processadas = (await db_session.execute(stmt_fotos)).scalars().all()
    assert len(fotos_processadas) > 0
    for foto in fotos_processadas:
        assert foto.url is not None
        assert foto.url.endswith(".webp")

    # 2. Segunda Execução (Teste de Idempotência Estrita)
    log_2 = await sync_svc.sincronizar_tudo(origem=OrigemSincronizacao.MANUAL)

    assert log_2.status == StatusSincronizacao.SUCESSO
    assert log_2.diarios_novos == 0
    assert log_2.diarios_atualizados == 0

    qtd_obras_2 = (await db_session.execute(stmt_obras)).scalar_one()
    qtd_diarios_2 = (await db_session.execute(stmt_diarios)).scalar_one()
    qtd_tarefas_2 = (await db_session.execute(stmt_tarefas)).scalar_one()

    assert qtd_obras_2 == qtd_obras_1
    assert qtd_diarios_2 == qtd_diarios_1
    assert qtd_tarefas_2 == qtd_tarefas_1

    # Restaura os usuários iniciais de demonstração ao final da suíte
    await garantir_usuarios_iniciais(db_session)
