"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_temperature: float = Field(default=0.1, ge=0, le=2)
    use_ollama: bool = False

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "change-me"

    allow_git_mutations: bool = False
    use_fixture_context: bool = True
    enable_template_fallbacks: bool = True
    artifact_root: Path = Path("artifacts")
    database_url: str | None = None

    @field_validator("api_base_url", "ollama_base_url", "neo4j_uri")
    @classmethod
    def require_service_url(cls, value: str) -> str:
        if "://" not in value:
            raise ValueError("must be a full service URL including its scheme")
        return value.rstrip("/")

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        path = (self.artifact_root.parent / "data" / "agentic-sdlc.db").resolve()
        return f"sqlite:///{path.as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
