from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Marketplace Assistant")
    app_env: str = Field(default="development")
    database_url: str = Field(default="sqlite:///./data/app.db")
    vector_store_dir: str = Field(default="./data/vectorstore")
    data_raw_dir: str = Field(default="./data/raw")
    data_processed_dir: str = Field(default="./data/processed")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    default_top_k: int = Field(default=5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url.removeprefix(prefix))
        return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
