import asyncio
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings, get_settings

# Proteção contra decompression bomb em imagens malformadas
Image.MAX_IMAGE_PIXELS = 50_000_000


class MediaProcessingError(Exception):
    """Falha ao decodificar ou converter imagem."""


@dataclass(slots=True)
class ImagemProcessada:
    conteudo: bytes
    largura: int
    altura: int
    tamanho_bytes: int
    content_type: str = "image/webp"


class MediaService:
    """Pipeline de processamento e otimização de imagens para economia de banda e storage."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def processar_foto(self, dados_originais: bytes) -> ImagemProcessada:
        """Síncrono (CPU-bound): converte para WebP, corrige EXIF e redimensiona mantendo proporção."""
        if not dados_originais:
            raise MediaProcessingError("Arquivo de imagem vazio.")
        try:
            with Image.open(io.BytesIO(dados_originais)) as img:
                # Corrige rotação baseada em tags EXIF de câmeras/celulares
                img = ImageOps.exif_transpose(img)

                # Converte para RGB caso esteja em RGBA/CMYK/paleta
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                largura, altura = img.size
                max_lado = self.settings.media_max_lado_px

                if largura > max_lado or altura > max_lado:
                    fator = min(max_lado / largura, max_lado / altura)
                    nova_largura = max(1, int(largura * fator))
                    nova_altura = max(1, int(altura * fator))
                    img = img.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
                    largura, altura = nova_largura, nova_altura

                buffer = io.BytesIO()
                img.save(
                    buffer,
                    format="WEBP",
                    quality=self.settings.media_qualidade_webp,
                    method=4,
                )
                conteudo_webp = buffer.getvalue()

                return ImagemProcessada(
                    conteudo=conteudo_webp,
                    largura=largura,
                    altura=altura,
                    tamanho_bytes=len(conteudo_webp),
                    content_type="image/webp",
                )
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise MediaProcessingError(f"Imagem inválida ou corrompida: {exc}") from exc

    async def processar_foto_async(self, dados_originais: bytes) -> ImagemProcessada:
        """Executa a compressão Pillow em thread separada para não bloquear o Event Loop do FastAPI."""
        return await asyncio.to_thread(self.processar_foto, dados_originais)
