from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ogso:ogso@localhost:5432/ogso"
    secret_key: str = "change-me"
    admin_email: str = "admin@ogso.so"
    admin_password: str = "admin"
    anthropic_api_key: str = ""  # Optional — only for POST /search/policy
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "papers"
    jina_api_key: str = ""
    allowed_origins: str = "http://localhost:3000"
    environment: str = "development"
    version: str = "1.0.0"

    # JWT
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
