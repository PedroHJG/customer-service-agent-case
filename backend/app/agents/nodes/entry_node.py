"""
Porta de entrada de cada mensagem: decide se ela vai para o agente ou para a resposta padrão
(circuit breaker aberto) e, quando o histórico fica longo, troca o transcript pelo resumo.
"""

import logging
from typing import Any

from app.agents.prompts import strip_user_metadata
from app.agents.scope_classifier import is_in_scope
from app.agents.state import AgentState
from app.agents.summarizer import count_user_turns, summarize
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def entry_node(state: AgentState) -> dict[str, Any]:
    settings = get_settings()
    incoming = state["incoming"]
    updates: dict[str, Any] = {}

    if state.get("breaker_open"):
        # Breaker aberto: só o classificador barato roda; o modelo principal não é chamado
        if not await is_in_scope(strip_user_metadata(incoming)):
            return {"route": "circuit_open"}
        logger.info("Cliente voltou ao escopo: fechando o circuit breaker")
        updates.update(breaker_open=False, off_topic_streak=0)

    transcript = state.get("messages", [])
    user_message = {"role": "user", "content": incoming}

    summary = None
    if count_user_turns(transcript) >= settings.summary_after_turns:
        summary = await summarize(transcript)

    if summary is None:
        updates.update(messages=[user_message], turn_start=len(transcript))
    else:
        # "" = nenhum turno no escopo para resumir: o transcript recomeça só com a nova mensagem
        content = f"<resumo_da_conversa>\n{summary}\n</resumo_da_conversa>\n\n{incoming}" if summary else incoming
        logger.info("Histórico compactado: %d turnos viraram um resumo", count_user_turns(transcript))
        updates.update(messages={"replace": [{"role": "user", "content": content}]}, turn_start=0)

    return {**updates, "history": [user_message], "route": "agent"}
