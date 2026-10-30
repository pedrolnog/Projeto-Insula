import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_endpoint_sync_manual_e_logs():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Dispara sincronização via API
        resp_post = await client.post("/api/v1/sync")
        assert resp_post.status_code == 200
        dados_log = resp_post.json()
        assert dados_log["status"] == "sucesso"
        assert dados_log["origem"] == "manual"
        assert dados_log["id"] > 0

        # 2. Consulta histórico de logs
        resp_logs = await client.get("/api/v1/sync/logs")
        assert resp_logs.status_code == 200
        lista_logs = resp_logs.json()
        assert isinstance(lista_logs, list)
        assert len(lista_logs) > 0
        assert lista_logs[0]["id"] == dados_log["id"]
