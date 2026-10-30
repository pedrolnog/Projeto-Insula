from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin
from app.models.enums import OrigemSincronizacao, StatusSincronizacao, enum_column


class LogSincronizacao(IdMixin, Base):
    """Uma execução da rotina de ingestão do Sienge (auditoria, observabilidade e controle de cota)."""

    __tablename__ = "logs_sincronizacao"

    origem: Mapped[OrigemSincronizacao] = mapped_column(enum_column(OrigemSincronizacao))
    status: Mapped[StatusSincronizacao] = mapped_column(
        enum_column(StatusSincronizacao), default=StatusSincronizacao.EXECUTANDO, index=True
    )
    # Nulo = sincronização de todas as obras.
    obra_id: Mapped[int | None] = mapped_column(
        ForeignKey("obras.id", ondelete="SET NULL"), index=True
    )

    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    diarios_novos: Mapped[int] = mapped_column(default=0)
    diarios_atualizados: Mapped[int] = mapped_column(default=0)
    fotos_processadas: Mapped[int] = mapped_column(default=0)
    requisicoes_sienge: Mapped[int] = mapped_column(default=0)

    mensagem_erro: Mapped[str | None] = mapped_column(Text)
    detalhes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    @property
    def duracao_ms(self) -> int | None:
        if self.detalhes and "duracao_ms" in self.detalhes:
            return int(self.detalhes["duracao_ms"])
        if self.iniciado_em and self.finalizado_em:
            return max(0, int((self.finalizado_em - self.iniciado_em).total_seconds() * 1000))
        return None
