from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.obra import Obra


class Empresa(IdMixin, TimestampMixin, Base):
    """Topo da hierarquia: a construtora/incorporadora dona dos empreendimentos."""

    __tablename__ = "empresas"

    nome: Mapped[str] = mapped_column(String(200))
    cnpj: Mapped[str | None] = mapped_column(String(14), unique=True)
    ativo: Mapped[bool] = mapped_column(default=True)

    obras: Mapped[list["Obra"]] = relationship(back_populates="empresa")
