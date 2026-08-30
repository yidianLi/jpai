"""AI数智化资产管理系统 - 配置"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI数智化资产管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    AI_DB_HOST: str = "127.0.0.1"
    AI_DB_PORT: int = 3306
    AI_DB_USER: str = "root"
    AI_DB_PASSWORD: str = "123456"
    AI_DB_NAME: str = "ai_asset_db"

    SOURCE_DB_HOST: str = "127.0.0.1"
    SOURCE_DB_PORT: int = 3306
    SOURCE_DB_USER: str = "readonly"
    SOURCE_DB_PASSWORD: str = "readonly"
    SOURCE_DB_NAME: str = "jpsoft_db4"

    JP_API_BASE: str = ""
    JP_API_TOKEN: str = ""
    USE_JP_API: bool = False

    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    LLM_ENABLED: bool = True

    SECRET_KEY: str = "ai-asset-mgmt-secret-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    SYNC_HOUR: int = 2
    SYNC_ENABLED: bool = True
    RESIDUAL_RATE: float = 0.05
    IDLE_THRESHOLD_DAYS: int = 90
    EXPIRE_RED_DAYS: int = 90
    EXPIRE_YELLOW_DAYS: int = 180

    class Config:
        env_file = ".env"


settings = Settings()
