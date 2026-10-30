from app.clients.storage.base import StorageClient
from app.clients.storage.local import LocalStorageClient
from app.clients.storage.s3 import S3StorageClient
from app.core.config import Settings, get_settings


def get_storage_client(settings: Settings | None = None) -> StorageClient:
    s = settings or get_settings()
    if s.storage_local:
        return LocalStorageClient(s)
    return S3StorageClient(s)


__all__ = ["LocalStorageClient", "S3StorageClient", "StorageClient", "get_storage_client"]
