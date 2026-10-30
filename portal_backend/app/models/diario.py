from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SiengeMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.foto import FotoDiario
    from app.models.obra import Obra
    from app.models.tarefa import TarefaDiario


class DiarioObra(IdMixin, TimestampMixin, SiengeMixin, Base):
    """Diário de obra (um por dia por obra). Origem: /construction-daily-report."""

    __tablename__ = "diarios_obra"
    __table_args__ = (
        # Idempotência: o id do diário no Sienge é único apenas dentro da obra.
        UniqueConstraint("obra_id", "sienge_diario_id"),
        Index("ix_diarios_obra_obra_id_data", "obra_id", "data"),
    )

    obra_id: Mapped[int] = mapped_column(ForeignKey("obras.id", ondelete="CASCADE"))
    sienge_diario_id: Mapped[int]

    data: Mapped[date]
    dia_semana: Mapped[str | None] = mapped_column(String(20))
    responsavel: Mapped[str | None] = mapped_column(String(100))
    observacoes: Mapped[str | None] = mapped_column(Text)
    indice_pluviometrico: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    # Estruturas pequenas e sem consulta própria ficam em JSONB:
    # turnos: [{descricao, inicio, fim, clima}], ocorrencias: [{descricao, tipo}]
    turnos: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    ocorrencias: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    # Usado na sincronização incremental: só rebaixa se mudou no Sienge.
    sienge_criado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sienge_modificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Permite ao admin ocultar um diário específico do portal.
    publicado: Mapped[bool] = mapped_column(default=True)

    obra: Mapped["Obra"] = relationship(back_populates="diarios")
    tarefas: Mapped[list["TarefaDiario"]] = relationship(
        back_populates="diario", cascade="all, delete-orphan", order_by="TarefaDiario.id"
    )
    fotos: Mapped[list["FotoDiario"]] = relationship(
        back_populates="diario", cascade="all, delete-orphan", order_by="FotoDiario.ordem"
    )
