from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def now_local() -> datetime:
    """Agora no fuso da loja; com REFERENCE_DATE definido, mantém a hora real e troca só a data."""
    settings = get_settings()
    now = datetime.now(ZoneInfo(settings.timezone))
    if settings.reference_date:
        now = now.replace(year=settings.reference_date.year, month=settings.reference_date.month,
                          day=settings.reference_date.day)
    return now
