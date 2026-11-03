"""
Memória das conversas: lê e apaga threads do checkpointer do LangGraph e converte o histórico
(formato Anthropic) para UIMessage, que é o que o useChat usa para redesenhar a conversa.
"""

import json
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.prompts import strip_user_metadata
from app.agents.tools import TOOLS
from app.models.schemas import ui_message
from app.services.llm_service import visible_blocks


def thread_config(chat_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": chat_id}}


async def get_history(graph: CompiledStateGraph, chat_id: str) -> list[dict[str, Any]]:
    snapshot = await graph.aget_state(thread_config(chat_id))
    return to_ui_messages(chat_id, snapshot.values.get("messages", []))


async def delete_history(checkpointer: BaseCheckpointSaver, chat_id: str) -> None:
    await checkpointer.adelete_thread(chat_id)


def to_ui_messages(chat_id: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Agrupa como o useChat faz no streaming: cada pergunta do cliente vira uma UIMessage `user`,
    e tudo que o agente fez até responder (textos, tools, guardrail) vira uma única UIMessage `assistant`.
    """
    ui_messages: list[dict[str, Any]] = []
    assistant_parts: list[dict[str, Any]] = []
    pending_tools: dict[str, dict[str, Any]] = {}

    def flush_assistant() -> None:
        if assistant_parts:
            ui_messages.append(ui_message(f"{chat_id}-{len(ui_messages)}", "assistant", list(assistant_parts)))
            assistant_parts.clear()

    for message in messages:
        content = message["content"]

        if message["role"] == "user" and isinstance(content, str):
            flush_assistant()
            text_part = {"type": "text", "text": strip_user_metadata(content)}
            ui_messages.append(ui_message(f"{chat_id}-{len(ui_messages)}", "user", [text_part]))

        elif message["role"] == "user":
            # Resultados de tools: completam as partes de tool abertas no turno do assistente
            for block in content:
                part = pending_tools.pop(block.get("tool_use_id", ""), None)
                if part is None:
                    continue
                if block.get("is_error"):
                    part.update(state="output-error", errorText="Falha na consulta")
                else:
                    part.update(state="output-available", output=json.loads(block["content"]))

        else:
            assistant_parts.append({"type": "step-start"})
            for block in visible_blocks(content):
                if block["type"] == "text":
                    assistant_parts.append({"type": "text", "text": block["text"], "state": "done"})
                elif block["type"] == "tool_use" and block["name"] in TOOLS and TOOLS[block["name"]].silent:
                    reason = block["input"].get("motivo", "")
                    assistant_parts.append({"type": "data-guardrail", "data": {"reason": reason}})
                elif block["type"] == "tool_use":
                    part = {
                        "type": f"tool-{block['name']}",
                        "toolCallId": block["id"],
                        "state": "input-available",
                        "input": block["input"],
                    }
                    pending_tools[block["id"]] = part
                    assistant_parts.append(part)

    flush_assistant()
    return ui_messages
