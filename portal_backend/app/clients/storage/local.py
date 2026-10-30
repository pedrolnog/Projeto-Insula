import asyncio
from pathlib import Path

from app.clients.storage.base import StorageClient
from app.core.config import Settings


class LocalStorageClient(StorageClient):
    """Armazenamento local em disco, ideal para desenvolvimento e testes sem Cloudflare R2/S3."""

    def __init__(self, settings: Settings) -> None:
        self.diretorio_base = Path(settings.storage_local_dir).resolve()
        self.diretorio_base.mkdir(parents=True, exist_ok=True)
        self.public_base_url = (settings.storage_public_base_url or "/media").rstrip("/")

    async def salvar(self, chave: str, conteudo: bytes, content_type: str = "image/webp") -> str:
        chave_limpa = chave.replace("\\", "/").lstrip("/")
        caminho_arquivo = (self.diretorio_base / chave_limpa).resolve()
        if not caminho_arquivo.is_relative_to(self.diretorio_base):
            raise ValueError(f"Caminho de storage inválido: {chave}")

        def _write() -> None:
            caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
            caminho_arquivo.write_bytes(conteudo)

        await asyncio.to_thread(_write)
        return f"{self.public_base_url}/{chave_limpa}"

    async def remover(self, chave: str) -> bool:
        chave_limpa = chave.replace("\\", "/").lstrip("/")
        caminho_arquivo = (self.diretorio_base / chave_limpa).resolve()
        if not caminho_arquivo.is_relative_to(self.diretorio_base):
            return False

        def _delete() -> bool:
            if caminho_arquivo.exists():
                caminho_arquivo.unlink()
                return True
            return False

        return await asyncio.to_thread(_delete)
