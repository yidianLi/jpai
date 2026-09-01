"""AI数智化资产管理系统 - 配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "简普数智资产管理后台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CREATE_TABLES_ON_STARTUP: bool = False
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str = "http://localhost:8080,http://127.0.0.1:8080"

    AI_DB_HOST: str = "127.0.0.1"
    AI_DB_PORT: int = 3306
    AI_DB_USER: str = "root"
    AI_DB_PASSWORD: str = ""
    AI_DB_NAME: str = "ai_asset_db"

    SOURCE_DB_HOST: str = "127.0.0.1"
    SOURCE_DB_PORT: int = 3306
    SOURCE_DB_USER: str = "root"
    SOURCE_DB_PASSWORD: str = "aiasset2026"
    SOURCE_DB_NAME: str = "jpsoft_db4"

    JP_API_BASE: str = ""
    JP_API_TOKEN: str = ""
    USE_JP_API: bool = False

    # 大模型配置：provider=ollama(本地) 或 openai(线上兼容接口)
    LLM_PROVIDER: str = "openai"
    LLM_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ENVIRONMENT: str = "development"
    MIGRATIONS_DIR: str = "sql/migrations"

    SYNC_HOUR: int = 2
    SYNC_ENABLED: bool = True
    RESIDUAL_RATE: float = 0.05
    IDLE_THRESHOLD_DAYS: int = 90
    EXPIRE_RED_DAYS: int = 90
    EXPIRE_YELLOW_DAYS: int = 180

    class Config:
        env_file = ".env"


settings = Settings()

if settings.ENVIRONMENT.lower() in {"production", "prod"}:
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be configured with at least 32 characters in production")
    if not settings.AI_DB_PASSWORD:
        raise RuntimeError("AI_DB_PASSWORD must be configured in production")
