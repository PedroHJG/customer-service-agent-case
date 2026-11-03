"""Recebe a mensagem da view, executa o grafo do agente e devolve o stream no protocolo do frontend."""

import logging
from collections.abc import AsyncIterator
from uuid import uuid4

import anthropic
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from app.agents.graph import RECURSION_LIMIT
from app.agents.prompts import format_user_message
from app.controllers.memory_manager import thread_config
from app.services import ui_stream

logger = logging.getLogger(__name__)

GENERIC_ERROR = "Tive um problema para responder agora. Pode tentar de novo em instantes?"


async def stream_chat(graph: CompiledStateGraph, chat_id: str, text: str) -> AsyncIterator[str]:
    yield ui_stream.sse(ui_stream.start(f"msg_{uuid4().hex}"))

    config = {**thread_config(chat_id), "recursion_limit": RECURSION_LIMIT}
    try:
        # stream_mode="custom" entrega exatamente o que os nós escreveram com get_stream_writer()
        async for event in graph.astream(
            {"incoming": format_user_message(text)},
            config=config,
            stream_mode="custom",
        ):
            yield ui_stream.sse(event)
    except GraphRecursionError:
        logger.warning("Limite de passos do agente atingido no chat %s", chat_id)
        yield ui_stream.sse(ui_stream.error(GENERIC_ERROR))
    except anthropic.APIStatusError as exc:
        logger.error("Erro da API Anthropic (%s) no chat %s: %s", exc.status_code, chat_id, exc.message)
        yield ui_stream.sse(ui_stream.error(GENERIC_ERROR))
    except anthropic.APIConnectionError:
        logger.error("Sem conexão com a API Anthropic no chat %s", chat_id)
        yield ui_stream.sse(ui_stream.error(GENERIC_ERROR))

    yield ui_stream.sse(ui_stream.finish())
    yield ui_stream.SSE_DONE
