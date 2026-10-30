"""Base declarativa e mixins reutilizáveis de todos os models.

Para mudar um comportamento comum (ex.: adicionar `criado_por` em todas as tabelas),
altere o mixin aqui e gere uma nova migração; não é preciso tocar em cada model.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nomes determinísticos para constraints/índices: o Alembic consegue
# renomear/remover constraints de forma previsível em migrações futuras.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class IdMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SiengeMixin:
    """Campos de rastreio para registros vindos do Sienge.

    `dados_sienge` guarda o payload bruto da API. Se for pedido um dado novo
    na tela, ele já está salvo aqui: basta expô-lo no schema ou promovê-lo a
    coluna própria numa migração, sem precisar rebaixar nada do Sienge.
    """

    dados_sienge: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sincronizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
