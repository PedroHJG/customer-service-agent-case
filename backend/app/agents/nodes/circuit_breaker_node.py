"""Resposta padrão com o circuit breaker aberto: texto salvo, sem chamada ao modelo principal."""

from typing import Any
from uuid import uuid4

from langgraph.config import get_stream_writer

from app.agents.prompts import CIRCUIT_OPEN_REASON, CIRCUIT_OPEN_REPLY
from app.agents.state import AgentState
from app.services import ui_stream


async def circuit_breaker_node(state: AgentState) -> dict[str, Any]:
    write = get_stream_writer()
    write(ui_stream.start_step())
    write(ui_stream.data_part("guardrail", {"reason": CIRCUIT_OPEN_REASON}))
    block_id = f"txt_{uuid4().hex}"
    write(ui_stream.text_start(block_id))
    write(ui_stream.text_delta(block_id, CIRCUIT_OPEN_REPLY))
    write(ui_stream.text_end(block_id))
    write(ui_stream.finish_step())

    # Só vai para o histórico da UI: o transcript do Claude não recebe este turno
    reply = {"role": "assistant", "content": [{"type": "circuit_breaker", "text": CIRCUIT_OPEN_REPLY}]}
    return {"history": [{"role": "user", "content": state["incoming"]}, reply]}
