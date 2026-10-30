from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.jobs.scheduler import iniciar_scheduler, parar_scheduler
from app.routers import admin, auth, health, minha_obra, sync
from app.services.seed_service import garantir_usuarios_iniciais

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante usuários e dados de demonstração apenas quando o Mock do Sienge estiver habilitado
    if settings.sienge_use_mock and settings.app_env in ("development", "dev", "local", "test"):
        async with AsyncSessionLocal() as session:
            await garantir_usuarios_iniciais(session)
    # Inicia o agendador periódico APScheduler
    iniciar_scheduler()
    yield
    # Encerra o agendador e limpa as conexões com o PostgreSQL
    parar_scheduler()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="BFF do Portal do Condômino. Lê apenas do banco local; o Sienge é acessado só pela camada de ingestão.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir mídias locais em desenvolvimento se não estiver usando Cloudflare R2 / S3
# Em produção, o tráfego de mídia é 100% descarregado para a CDN/Object Storage com Cache-Control imutável.
if settings.storage_local:
    caminho_media = Path(settings.storage_local_dir).resolve()
    caminho_media.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(caminho_media)), name="media")


@app.middleware("http")
async def adicionar_cache_control_midia(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/media/") and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

# Rotas da API
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(minha_obra.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(sync.router, prefix=settings.api_v1_prefix)
