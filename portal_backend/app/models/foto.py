from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import StatusFoto, enum_column

if TYPE_CHECKING:
    from app.models.diario import DiarioObra
    from app.models.unidade import Unidade


class FotoDiario(IdMixin, TimestampMixin, Base):
    """Anexo de imagem do diário, já convertido para WebP no Object Storage."""

    __tablename__ = "fotos_diario"
    __table_args__ = (
        UniqueConstraint("diario_id", "sienge_attachment_number"),
        Index(
            "ix_fotos_diario_unidade_parcial",
            "unidade_id",
            "status",
            "publicado",
            postgresql_where=text("unidade_id IS NOT NULL"),
        ),
        Index(
            "ix_fotos_diario_geral_parcial",
            "diario_id",
            "ordem",
            postgresql_where=text("unidade_id IS NULL AND publicado = true"),
        ),
    )

    diario_id: Mapped[int] = mapped_column(
        ForeignKey("diarios_obra.id", ondelete="CASCADE"), index=True
    )
    unidade_id: Mapped[int | None] = mapped_column(
        ForeignKey("unidades.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sienge_attachment_number: Mapped[int]

    nome_arquivo_original: Mapped[str | None] = mapped_column(String(255))
    descricao: Mapped[str | None] = mapped_column(Text)
    local: Mapped[str | None] = mapped_column(String(200))  # `location` no Sienge
    ordem: Mapped[int] = mapped_column(default=0)

    # Preenchidos após o pipeline de mídia (download -> WebP -> upload).
    status: Mapped[StatusFoto] = mapped_column(
        enum_column(StatusFoto), default=StatusFoto.PENDENTE, index=True
    )
    # Quarentena / Moderação: se False, a foto aguarda classificação de um Admin
    # e NUNCA aparece para nenhum condômino (nem no feed geral, nem nas unidades).
    publicado: Mapped[bool] = mapped_column(
        default=True, server_default="true", index=True
    )
    storage_key: Mapped[str | None] = mapped_column(String(500))
    url: Mapped[str | None] = mapped_column(String(500))
    largura: Mapped[int | None]
    altura: Mapped[int | None]
    tamanho_bytes: Mapped[int | None]
    erro: Mapped[str | None] = mapped_column(Text)

    diario: Mapped["DiarioObra"] = relationship(back_populates="fotos")
    unidade: Mapped["Unidade | None"] = relationship(back_populates="fotos")
