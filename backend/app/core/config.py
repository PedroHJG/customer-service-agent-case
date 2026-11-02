from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    anthropic_api_key: str
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "medium"
    claude_max_tokens: int = 64000

    database_url: str = "postgresql://emporio:emporio@localhost:5432/emporio"
    frontend_origin: str = "http://localhost:3000"

    data_dir: Path = BASE_DIR / "data"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # Limite de tamanho da mensagem do cliente (proteção de custo e de abuso)
    max_user_message_chars: int = 2000


@lru_cache
def get_settings() -> Settings:
    return Settings()
