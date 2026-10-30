from abc import ABC, abstractmethod


class StorageClient(ABC):
    """Interface abstrata para armazenamento de objetos/arquivos."""

    @abstractmethod
    async def salvar(self, chave: str, conteudo: bytes, content_type: str = "image/webp") -> str:
        """Salva o arquivo e retorna sua URL pública acessível."""

    @abstractmethod
    async def remover(self, chave: str) -> bool:
        """Remove o arquivo se existir."""
