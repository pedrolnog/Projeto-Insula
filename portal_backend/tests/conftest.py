import os
from collections.abc import AsyncGenerator

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Garante que os testes automatizados rodem SEMPRE com o Mock hermético e em um banco de testes
# 100% isolado (`portal_condomino_test`), NUNCA tocando ou truncando o banco principal (`portal_condomino`).
os.environ["SIENGE_USE_MOCK"] = "true"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://portal:portal@localhost:5433/portal_condomino_test"
)

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.database import AsyncSessionLocal, engine
from app.models import Base


@pytest.fixture(scope="session", autouse=True)
async def _preparar_e_encerrar_banco_teste():
    # Cria o banco `portal_condomino_test` caso ainda não exista no container PostgreSQL
    conn = await asyncpg.connect("postgresql://portal:portal@localhost:5433/postgres")
    try:
        existe = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'portal_condomino_test'"
        )
        if not existe:
            await conn.execute("CREATE DATABASE portal_condomino_test")
    finally:
        await conn.close()

    async with engine.begin() as conn_orm:
        await conn_orm.run_sync(Base.metadata.create_all)
        await conn_orm.execute(
            text(
                "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS termo_privacidade_aceito_em TIMESTAMP WITH TIME ZONE;"
            )
        )

    yield
    await engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
