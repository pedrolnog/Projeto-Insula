from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SiengeMixin, TimestampMixin
from app.models.enums import TipoTarefa, enum_column

if TYPE_CHECKING:
    from app.models.diario import DiarioObra
    from app.models.unidade import Unidade


class TarefaDiario(IdMixin, TimestampMixin, SiengeMixin, Base):
    """Tarefa executada no dia (plannedTasks + detachedTasks do Sienge).

    Tarefas planejadas não trazem descrição no diário, só `taskId`; a
    descrição é resolvida pelo planejamento da obra durante a ingestão.
    Se `unidade_id` for nulo, é uma tarefa geral do edifício; se preenchido,
    é uma atividade exclusiva da reforma daquela unidade.
    """

    __tablename__ = "tarefas_diario"
    __table_args__ = (UniqueConstraint("diario_id", "tipo", "sienge_item_id"),)

    diario_id: Mapped[int] = mapped_column(
        ForeignKey("diarios_obra.id", ondelete="CASCADE"), index=True
    )
    unidade_id: Mapped[int | None] = mapped_column(
        ForeignKey("unidades.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo: Mapped[TipoTarefa] = mapped_column(enum_column(TipoTarefa))

    sienge_item_id: Mapped[int]  # `id` do item dentro do diário
    sienge_tarefa_id: Mapped[int | None]  # `taskId` do planejamento (só planejadas)

    descricao: Mapped[str | None] = mapped_column(String(500))
    quantidade: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    unidade_medida: Mapped[str | None] = mapped_column(String(20))
    observacoes: Mapped[str | None] = mapped_column(Text)

    diario: Mapped["DiarioObra"] = relationship(back_populates="tarefas")
    unidade: Mapped["Unidade | None"] = relationship(back_populates="tarefas")
