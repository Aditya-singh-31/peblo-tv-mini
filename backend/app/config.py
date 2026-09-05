from __future__ import annotations

from typing import Any, Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    postgres_db: str = Field(default="peblo", alias="POSTGRES_DB")
    postgres_user: str = Field(default="peblo", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me_dev", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    database_url: str = Field(
        default="postgresql+psycopg://peblo:change_me_dev@db:5432/peblo",
        alias="DATABASE_URL",
    )

    jwt_secret: str = Field(default="change-me-in-dev", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_path: str = Field(default="./storage", alias="LOCAL_STORAGE_PATH")
    local_storage_url: str = Field(default="http://localhost:8000/storage", alias="LOCAL_STORAGE_URL")

    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://localhost:4173"],
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    cms_api_url: str = Field(default="http://localhost:8000", alias="CMS_API_URL")
    viewer_api_url: str = Field(default="http://localhost:8000", alias="VIEWER_API_URL")

    dev_editor_email: str | None = Field(default="editor@example.com", alias="DEV_EDITOR_EMAIL")
    dev_editor_password: str | None = Field(default="change_me_dev", alias="DEV_EDITOR_PASSWORD")
    dev_admin_email: str | None = Field(default="admin@example.com", alias="DEV_ADMIN_EMAIL")
    dev_admin_password: str | None = Field(default="change_me_dev", alias="DEV_ADMIN_PASSWORD")

    @field_validator("cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def parse_csv_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]


settings = Settings()
