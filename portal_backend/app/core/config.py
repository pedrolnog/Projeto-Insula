from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Portal do Condômino API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+asyncpg://portal:portal@localhost:5432/portal_condomino"
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Rate limit de login por IP (proteção contra picos de CPU do bcrypt e brute-force)
    login_rate_limit_max_requests: int = 15
    login_rate_limit_window_seconds: int = 60

    # Chave temporária para os endpoints de admin (substituída por JWT de admin na Fase 4).
    admin_api_key: str = ""

    sienge_use_mock: bool = True
    sienge_base_url: str = ""
    sienge_user: str = ""
    sienge_password: str = ""
    sienge_webhook_secret: str = ""
    sienge_timeout_seconds: int = 30
    sienge_max_retries: int = 3
    sienge_backoff_seconds: int = 5
    # Retry-After acima disso = cota esgotada; aborta em vez de esperar.
    sienge_max_wait_seconds: int = 60
    sienge_page_limit: int = 200

    sync_lookback_days: int = 7
    sync_fotos_por_execucao: int = 200
    sync_cron_hours: str = "6,18"
    sync_timezone: str = "America/Sao_Paulo"
    scheduler_enabled: bool = True

    media_max_lado_px: int = 1920
    media_qualidade_webp: int = 80

    # Se STORAGE_ENDPOINT_URL estiver vazio, as fotos são salvas em disco
    # (STORAGE_LOCAL_DIR) e servidas pela própria API em /media.
    storage_endpoint_url: str = ""
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_bucket: str = "portal-fotos"
    storage_public_base_url: str = ""
    storage_local_dir: str = "media"

    @property
    def storage_local(self) -> bool:
        return not self.storage_endpoint_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
