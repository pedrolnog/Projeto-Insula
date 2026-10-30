from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, SiengeMixin, TimestampMixin
from app.models.enums import FaseObra, enum_column

if TYPE_CHECKING:
    from app.models.diario import DiarioObra
    from app.models.empresa import Empresa
    from app.models.unidade import Unidade
    from app.models.usuario import Usuario


class Obra(IdMixin, TimestampMixin, SiengeMixin, Base):
    """Empreendimento/obra. Equivale ao `buildingId` (e `enterpriseId`) do Sienge."""

    __tablename__ = "obras"

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), index=True)

    sienge_building_id: Mapped[int] = mapped_column(unique=True)
    sienge_enterprise_id: Mapped[int | None] = mapped_column(index=True)

    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    endereco: Mapped[str | None] = mapped_column(String(300))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    situacao: Mapped[str | None] = mapped_column(String(50))  # texto livre vindo do Sienge

    percentual_concluido: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    data_inicio: Mapped[date | None]
    data_previsao_entrega: Mapped[date | None]
    imagem_capa_url: Mapped[str | None] = mapped_column(String(500))

    # Permite ocultar uma obra do portal sem apagá-la nem parar a sincronização.
    visivel_portal: Mapped[bool] = mapped_column(default=True)

    # Marco de inflexão (Ponto X): define se a visão principal é geral ou por unidade.
    fase_atual: Mapped[FaseObra] = mapped_column(
        enum_column(FaseObra, length=30),
        default=FaseObra.ESTRUTURAL_GERAL,
        server_default=FaseObra.ESTRUTURAL_GERAL.value,
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="obras")
    diarios: Mapped[list["DiarioObra"]] = relationship(
        back_populates="obra", order_by="desc(DiarioObra.data)"
    )
    unidades: Mapped[list["Unidade"]] = relationship(
        back_populates="obra", cascade="all, delete-orphan", order_by="Unidade.identificador"
    )
    usuarios: Mapped[list["Usuario"]] = relationship(
        secondary="usuarios_obras", back_populates="obras"
    )
