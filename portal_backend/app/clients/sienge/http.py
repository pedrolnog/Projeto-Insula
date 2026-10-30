"""Cliente HTTP real da API REST do Sienge (Basic Auth)."""
import asyncio
import logging
import random
from datetime import date
from typing import Any

import httpx

from app.clients.sienge.base import Json, SiengeClient
from app.clients.sienge.errors import SiengeError, SiengeNotFound, SiengeQuotaExceeded
from app.core.config import Settings

logger = logging.getLogger(__name__)

SIENGE_MAX_PAGE_LIMIT = 200


class HttpSiengeClient(SiengeClient):
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        super().__init__()
        if not settings.sienge_base_url:
            raise SiengeError("SIENGE_BASE_URL não configurada (ou use SIENGE_USE_MOCK=true)")
        self._s = settings
        self._http = httpx.AsyncClient(
            base_url=settings.sienge_base_url.rstrip("/") + "/",
            auth=(settings.sienge_user, settings.sienge_password),
            timeout=httpx.Timeout(settings.sienge_timeout_seconds),
            headers={"Accept": "application/json"},
            transport=transport,
        )

    async def fechar(self) -> None:
        await self._http.aclose()

    # --- Infra -----------------------------------------------------------
    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Faz a chamada com retry exponencial + jitter para 429/5xx/erros de rede.

        - Respeita o header Retry-After quando presente.
        - Se o Retry-After passar de SIENGE_MAX_WAIT_SECONDS, a cota diária
          acabou: lança SiengeQuotaExceeded na hora (não adianta esperar).
        """
        tentativa = 0
        while True:
            self.requisicoes += 1
            try:
                resp = await self._http.request(method, path.lstrip("/"), **kwargs)
            except httpx.TimeoutException as exc:
                if tentativa >= self._s.sienge_max_retries:
                    raise SiengeError(f"Timeout em {method} {path}: {exc}") from exc
                await self._esperar(tentativa, None, path, motivo="timeout")
                tentativa += 1
                continue
            except httpx.HTTPError as exc:
                if tentativa >= self._s.sienge_max_retries:
                    raise SiengeError(f"Falha de rede em {method} {path}: {exc}") from exc
                await self._esperar(tentativa, None, path, motivo="rede")
                tentativa += 1
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                if (
                    resp.status_code == 429
                    and retry_after is not None
                    and retry_after > self._s.sienge_max_wait_seconds
                ):
                    raise SiengeQuotaExceeded(
                        f"Cota do Sienge esgotada (Retry-After={retry_after}s)", status_code=429
                    )
                if tentativa >= self._s.sienge_max_retries:
                    if resp.status_code == 429:
                        raise SiengeQuotaExceeded("Sienge continua retornando 429", status_code=429)
                    raise SiengeError(
                        f"{resp.status_code} em {method} {path}", status_code=resp.status_code
                    )
                await self._esperar(
                    tentativa, retry_after, path, motivo=f"HTTP {resp.status_code}"
                )
                tentativa += 1
                continue

            if resp.status_code == 404:
                raise SiengeNotFound(f"404 em {method} {path}", status_code=404)
            if resp.status_code >= 400:
                raise SiengeError(
                    f"{resp.status_code} em {method} {path}: {resp.text[:300]}",
                    status_code=resp.status_code,
                )
            return resp

    async def _esperar(
        self, tentativa: int, retry_after: float | None, path: str, motivo: str = ""
    ) -> None:
        if retry_after is not None:
            espera = retry_after
        else:
            # Exponential backoff com jitter (0.75x a 1.25x) para evitar thundering herd
            base = self._s.sienge_backoff_seconds * (2**tentativa)
            espera = base * random.uniform(0.75, 1.25)
        espera = min(espera, float(self._s.sienge_max_wait_seconds))
        logger.warning(
            "Sienge (%s): nova tentativa em %.2fs (%s, tentativa %d/%d)",
            motivo or "retry",
            espera,
            path,
            tentativa + 1,
            self._s.sienge_max_retries,
        )
        await asyncio.sleep(espera)

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Json:
        resp = await self._request("GET", path, params=params)
        try:
            dados = resp.json()
        except ValueError as exc:
            raise SiengeError(
                f"Resposta JSON inválida em GET {path}: {resp.text[:200]}",
                status_code=resp.status_code,
            ) from exc
        if not isinstance(dados, dict):
            raise SiengeError(
                f"Formato inesperado em GET {path} (esperado objeto JSON)",
                status_code=resp.status_code,
            )
        return dados

    async def _paginar(self, path: str, params: dict[str, Any] | None = None) -> list[Json]:
        """Percorre todas as páginas (offset/limit) respeitando o teto de 200 itens do Sienge."""
        params = dict(params or {})
        limit = min(max(1, self._s.sienge_page_limit), SIENGE_MAX_PAGE_LIMIT)
        offset = 0
        resultados: list[Json] = []
        while True:
            dados = await self._get_json(path, {**params, "offset": offset, "limit": limit})
            pagina = dados.get("results") or []
            if not isinstance(pagina, list) or not pagina:
                return resultados
            resultados.extend(pagina)
            meta = dados.get("resultSetMetadata") or {}
            total = int(meta.get("count", len(resultados)))
            offset += len(pagina)
            if offset >= total or len(pagina) < limit:
                return resultados

    # --- Endpoints -------------------------------------------------------
    async def listar_empreendimentos(self) -> list[Json]:
        return await self._paginar("enterprises")

    async def listar_diarios(self, building_id: int, inicio: date, fim: date) -> list[Json]:
        return await self._paginar(
            "construction-daily-report",
            {"buildingId": building_id, "startDate": inicio.isoformat(), "endDate": fim.isoformat()},
        )

    async def obter_diario(self, building_id: int, diario_id: int) -> Json:
        return await self._get_json(f"construction-daily-report/{building_id}/{diario_id}")

    async def baixar_anexo(self, building_id: int, diario_id: int, attachment_number: int) -> bytes:
        resp = await self._request(
            "GET",
            f"construction-daily-report/{building_id}/{diario_id}/attachments/{attachment_number}",
            headers={"Accept": "*/*"},
        )
        return resp.content

    async def listar_tarefas_planejamento(self, building_id: int, building_unit_id: int) -> list[Json]:
        return await self._paginar(f"building-projects/{building_id}/sheets/{building_unit_id}/tasks")

    async def listar_medicoes(self, building_id: int) -> list[Json]:
        return await self._paginar("building-projects/progress-logs", {"buildingId": building_id})

    async def obter_medicao(self, building_id: int, measurement_number: int) -> Json:
        return await self._get_json(f"building-projects/{building_id}/progress-logs/{measurement_number}")

    async def listar_itens_medicao(
        self, building_id: int, measurement_number: int, building_unit_id: int
    ) -> list[Json]:
        return await self._paginar(
            f"building-projects/{building_id}/progress-logs/{measurement_number}/items/{building_unit_id}"
        )


def _parse_retry_after(valor: str | None) -> float | None:
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        return None  # formato data HTTP: ignoramos e usamos o backoff padrão
