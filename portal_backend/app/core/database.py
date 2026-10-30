from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Pool dimensionado para alta concorrência (750+ condôminos / unidades simultâneas):
# - pool_size=20 conexões quentes mantidas por worker
# - max_overflow=20 conexões extras sob pico (total até 40 por worker)
# - pool_timeout=30s evita falha prematura em rajadas de leitura
# - pool_recycle=1800s (30 min) recicla conexões antigas evitando desconexão silenciosa
# - pool_pre_ping=True valida saúde do socket antes de entregar à rota
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
