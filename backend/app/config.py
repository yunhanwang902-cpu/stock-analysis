from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ProTrade API"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Cache
    CACHE_TTL_SECONDS: int = 60

    # Data refresh
    WS_BROADCAST_INTERVAL: int = 10  # seconds

    # Auth
    SECRET_KEY: str = "protrade-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
