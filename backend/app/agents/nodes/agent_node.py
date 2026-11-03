"""Nó do LLM: chama o Claude em streaming e repassa cada pedaço para a UI em tempo real."""

from typing import Any
from uuid import uuid4

from langgraph.config import get_stream_writer

from app.agents.prompts import build_system
from app.agents.state import AgentState
from app.agents.tools import TOOL_DEFINITIONS, TOOLS
from app.services import ui_stream
from app.services.llm_service import client, request_params, visible_blocks

REFUSAL_TEXT = "Desculpe, não consigo ajudar com isso por aqui. Posso te ajudar com algo da loja?"


def _prepare_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**m, "content": visible_blocks(m["content"])} if m["role"] == "assistant" else m
        for m in messages
    ]


async def agent_node(state: AgentState) -> dict[str, Any]:
    write = get_stream_writer()
    write(ui_stream.start_step())

    # index do bloco no stream -> id do bloco de texto aberto na UI
    open_text_blocks: dict[int, str] = {}

    async with client.beta.messages.stream(
        **request_params(),
        system=build_system(),
        tools=TOOL_DEFINITIONS,
        messages=_prepare_history(state["messages"]),
    ) as stream:
        async for event in stream:
            if event.type == "content_block_start":
                block = event.content_block
                if block.type == "text":
                    open_text_blocks[event.index] = block_id = f"txt_{uuid4().hex}"
                    write(ui_stream.text_start(block_id))
                elif block.type == "tool_use" and not _is_silent(block.name):
                    write(ui_stream.tool_input_start(block.id, block.name))

            elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                if event.index in open_text_blocks:
                    write(ui_stream.text_delta(open_text_blocks[event.index], event.delta.text))

            elif event.type == "content_block_stop" and event.index in open_text_blocks:
                write(ui_stream.text_end(open_text_blocks.pop(event.index)))

        final = await stream.get_final_message()

    content = [block.model_dump(mode="json", exclude_none=True) for block in final.content]

    if final.stop_reason == "refusal":
        # Toda a cadeia de fallback recusou: responde algo neutro e mantém só os textos no histórico
        block_id = f"txt_{uuid4().hex}"
        write(ui_stream.text_start(block_id))
        write(ui_stream.text_delta(block_id, REFUSAL_TEXT))
        write(ui_stream.text_end(block_id))
        content = [b for b in content if b["type"] == "text"] + [{"type": "text", "text": REFUSAL_TEXT}]
    elif final.stop_reason == "tool_use":
        for block in visible_blocks(content):
            if block["type"] == "tool_use" and not _is_silent(block["name"]):
                write(ui_stream.tool_input_available(block["id"], block["name"], block["input"]))
    else:
        # Sem execução de tools neste turno: um tool_use sem tool_result quebraria a próxima chamada
        content = [b for b in content if b["type"] != "tool_use"]

    write(ui_stream.finish_step())
    message = {"role": "assistant", "content": content}
    return {"messages": [message], "history": [message], "stop_reason": final.stop_reason}


def _is_silent(tool_name: str) -> bool:
    tool = TOOLS.get(tool_name)
    return tool is not None and tool.silent
