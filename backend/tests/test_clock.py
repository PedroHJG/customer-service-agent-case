import time
from datetime import datetime

import pytest

from app.core import clock
from app.core.config import get_settings


@pytest.fixture
def reference(monkeypatch):
    def set_reference(value: str | None):
        if value is None:
            monkeypatch.delenv("REFERENCE_DATETIME", raising=False)
        else:
            monkeypatch.setenv("REFERENCE_DATETIME", value)
        get_settings.cache_clear()
        clock._offset.cache_clear()

    yield set_reference
    get_settings.cache_clear()
    clock._offset.cache_clear()


def test_data_e_hora_simuladas(reference):
    reference("2026-03-25T20:30")
    now = clock.now_local()
    assert (now.date().isoformat(), now.hour, now.minute) == ("2026-03-25", 20, 30)


def test_so_a_data_mantem_a_hora_real(reference):
    reference("2026-03-25")
    now = clock.now_local()
    assert now.date().isoformat() == "2026-03-25"
    assert now.hour == datetime.now(now.tzinfo).hour


def test_relogio_continua_andando(reference):
    reference("2026-03-25T20:30")
    before = clock.now_local()
    time.sleep(0.05)  # o relógio do Windows tem resolução de ~15 ms
    assert clock.now_local() > before
