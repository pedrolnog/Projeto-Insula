from app.clients.sienge.base import SiengeClient
from app.clients.sienge.errors import SiengeError, SiengeNotFound, SiengeQuotaExceeded
from app.clients.sienge.http import HttpSiengeClient
from app.clients.sienge.mock import MockSiengeClient
from app.core.config import Settings, get_settings


def get_sienge_client(settings: Settings | None = None) -> SiengeClient:
    s = settings or get_settings()
    if s.sienge_use_mock or not s.sienge_base_url:
        return MockSiengeClient()
    return HttpSiengeClient(s)


__all__ = [
    "HttpSiengeClient",
    "MockSiengeClient",
    "SiengeClient",
    "SiengeError",
    "SiengeNotFound",
    "SiengeQuotaExceeded",
    "get_sienge_client",
]
