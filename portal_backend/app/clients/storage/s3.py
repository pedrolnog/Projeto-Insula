import asyncio

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.clients.storage.base import StorageClient
from app.core.config import Settings


class S3StorageClient(StorageClient):
    """Cliente para Cloudflare R2, Supabase Storage ou AWS S3 compatível."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.storage_bucket
        self.public_base_url = (settings.storage_public_base_url or "").rstrip("/")
        self.endpoint_url = settings.storage_endpoint_url
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def salvar(self, chave: str, conteudo: bytes, content_type: str = "image/webp") -> str:
        chave_formatada = chave.replace("\\", "/").lstrip("/")

        def _upload():
            self._s3.put_object(
                Bucket=self.bucket,
                Key=chave_formatada,
                Body=conteudo,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )

        await asyncio.to_thread(_upload)

        if self.public_base_url:
            return f"{self.public_base_url}/{chave_formatada}"
        return f"{self.endpoint_url.rstrip('/')}/{self.bucket}/{chave_formatada}"

    async def remover(self, chave: str) -> bool:
        chave_formatada = chave.replace("\\", "/").lstrip("/")

        def _delete():
            try:
                self._s3.delete_object(Bucket=self.bucket, Key=chave_formatada)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_delete)
