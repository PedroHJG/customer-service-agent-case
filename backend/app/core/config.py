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
    # Tarefas auxiliares e frequentes (classificar escopo, resumir histórico) usam um modelo barato
    auxiliary_model: str = "claude-haiku-5-5"

    database_url: str = "postgresql://emporio:emporio@localhost:5433/emporio"
    frontend_origin: str = "http://localhost:3000"

    data_dir: Path = BASE_DIR / "data"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # Limite de tamanho da mensagem do cliente (proteção de custo e de abuso)
    max_user_message_chars: int = 2000

    # Circuit breaker: após N mensagens seguidas fora do escopo, o Opus deixa de ser chamado
    out_of_scope_threshold: int = 5
    # Memória: a partir de N turnos do cliente, o histórico vira um resumo (só dos turnos no escopo)
    summary_after_turns: int = 12

    timezone: str = "America/Campo_Grande"
    # Momento simulado (ISO: "2026-03-25T19:30" ou só "2026-03-25") a partir do qual o relógio da loja
    # anda em tempo real. Os pedidos dos CSVs são de out/2025 a mar/2026: com a data real todos os
    # prazos de troca já teriam vencido. Vazio = relógio real.
    reference_datetime: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
