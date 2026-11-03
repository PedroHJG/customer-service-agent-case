"""Fim de turno respondido pelo agente: atualiza o contador de mensagens seguidas fora do escopo."""

import logging
from typing import Any

from app.agents.state import AgentState
from app.agents.summarizer import is_off_topic
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def finalize_node(state: AgentState) -> dict[str, Any]:
    turn = state["messages"][state.get("turn_start", 0) :]
    if not is_off_topic(turn):
        return {"off_topic_streak": 0}

    streak = state.get("off_topic_streak", 0) + 1
    breaker_open = streak >= get_settings().out_of_scope_threshold
    if breaker_open:
        logger.info("Circuit breaker aberto após %d mensagens seguidas fora do escopo", streak)
    return {"off_topic_streak": streak, "breaker_open": breaker_open}
