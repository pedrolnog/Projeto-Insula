from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import PerfilUsuario, enum_column

if TYPE_CHECKING:
    from app.models.obra import Obra
    from app.models.unidade import Unidade


# Vínculo condômino <-> obra (base do multi-tenancy).
# Um condômino pode investir em mais de uma obra.
usuarios_obras = Table(
    "usuarios_obras",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("obra_id", ForeignKey("obras.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("criado_em", DateTime(timezone=True), server_default=func.now()),
)


class Usuario(IdMixin, TimestampMixin, Base):
    __tablename__ = "usuarios"

    cpf: Mapped[str] = mapped_column(String(11), unique=True)  # só dígitos
    nome: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(20))
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[PerfilUsuario] = mapped_column(
        enum_column(PerfilUsuario), default=PerfilUsuario.CONDOMINO
    )
    ativo: Mapped[bool] = mapped_column(default=True)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    termo_privacidade_aceito_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    obras: Mapped[list["Obra"]] = relationship(
        secondary=usuarios_obras, back_populates="usuarios"
    )
    unidades: Mapped[list["Unidade"]] = relationship(
        secondary="usuarios_unidades", back_populates="usuarios"
    )
