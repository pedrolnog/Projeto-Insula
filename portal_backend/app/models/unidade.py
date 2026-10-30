from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin
from app.models.enums import StatusReformaUnidade, enum_column

if TYPE_CHECKING:
    from app.models.foto import FotoDiario
    from app.models.obra import Obra
    from app.models.tarefa import TarefaDiario
    from app.models.usuario import Usuario


# Vínculo condômino <-> unidade (foco na fase de reformas e acabamentos internos).
usuarios_unidades = Table(
    "usuarios_unidades",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column(
        "unidade_id",
        ForeignKey("unidades.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column("criado_em", DateTime(timezone=True), server_default=func.now()),
)


class Unidade(IdMixin, TimestampMixin, Base):
    """Unidade autônoma do empreendimento (ex.: Apto 302) acompanhada no Ponto X (Reformas)."""

    __tablename__ = "unidades"
    __table_args__ = (UniqueConstraint("obra_id", "identificador"),)

    obra_id: Mapped[int] = mapped_column(
        ForeignKey("obras.id", ondelete="CASCADE"), index=True
    )
    identificador: Mapped[str] = mapped_column(String(100))  # ex.: "Apto 302"
    sienge_unit_id: Mapped[int | None] = mapped_column(nullable=True, index=True)

    status_reforma: Mapped[StatusReformaUnidade] = mapped_column(
        enum_column(StatusReformaUnidade, length=30),
        default=StatusReformaUnidade.NAO_INICIADA,
        server_default=StatusReformaUnidade.NAO_INICIADA.value,
    )
    percentual_reforma: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        server_default="0.00",
    )
    observacoes_reforma: Mapped[str | None] = mapped_column(Text, nullable=True)

    obra: Mapped["Obra"] = relationship(back_populates="unidades")
    usuarios: Mapped[list["Usuario"]] = relationship(
        secondary=usuarios_unidades, back_populates="unidades"
    )
    fotos: Mapped[list["FotoDiario"]] = relationship(
        back_populates="unidade", order_by="FotoDiario.ordem"
    )
    tarefas: Mapped[list["TarefaDiario"]] = relationship(
        back_populates="unidade", order_by="TarefaDiario.id"
    )
