"""Relógio da loja, controlável pelo .env (REFERENCE_DATETIME) para testar prazos e horário de atendimento."""

from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


@lru_cache
def _offset() -> timedelta:
    """Diferença fixa entre o momento simulado e o real, calculada uma vez (na subida do servidor)."""
    reference = get_settings().reference_datetime
    if not reference:
        return timedelta(0)

    real_now = datetime.now(_tz())
    simulated = datetime.fromisoformat(reference)
    if "T" not in reference and " " not in reference.strip():
        # Só a data: mantém a hora real do dia
        simulated = datetime.combine(simulated.date(), real_now.time())
    if simulated.tzinfo is None:
        simulated = simulated.replace(tzinfo=_tz())
    return simulated - real_now


def now_local() -> datetime:
    """Agora no fuso da loja. Com REFERENCE_DATETIME, o relógio parte do momento simulado e segue andando."""
    return datetime.now(_tz()) + _offset()
