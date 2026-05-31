from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values can come from the process environment or from a local `.env` file.
    Secrets such as `LLM_API_KEY` must be provided by the environment and should
    never be hard-coded in source control.
    """

    app_name: str = Field(default="hoop-insight", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    database_url: str = Field(
        default="sqlite:///../data/cache/hoop_insight.db",
        alias="DATABASE_URL",
    )
    nba_cache_dir: str = Field(default="../data/cache/nba", alias="NBA_CACHE_DIR")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    demo_data_dir: str = Field(default="../data/processed", alias="DEMO_DATA_DIR")
    llm_provider: str = Field(default="openai-compatible", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="", alias="LLM_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so the app reads environment variables once."""

    return Settings()
