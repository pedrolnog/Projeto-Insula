"""adiciona_termo_privacidade_aceito_em

Revision ID: 85571d33037a
Revises: 16712adce970
Create Date: 2026-10-22 16:04:19.641751
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '85571d33037a'
down_revision: Union[str, None] = '16712adce970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("termo_privacidade_aceito_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "termo_privacidade_aceito_em")
