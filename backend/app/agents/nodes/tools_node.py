"""Nó das ferramentas: executa em paralelo os tool_use pedidos pelo Claude e avisa a UI do resultado."""

import asyncio
import json
import logging
from typing import Any

from langgraph.config import get_stream_writer

from app.agents.state import AgentState
from app.agents.tools import TOOLS, ToolExecutionError, execute_tool
from app.services import ui_stream
from app.services.llm_service import visible_blocks

logger = logging.getLogger(__name__)


async def tools_node(state: AgentState) -> dict[str, Any]:
    write = get_stream_writer()
    last_message = state["messages"][-1]
    tool_uses = [b for b in visible_blocks(last_message["content"]) if b["type"] == "tool_use"]

    async def run(block: dict[str, Any]) -> dict[str, Any]:
        silent = block["name"] in TOOLS and TOOLS[block["name"]].silent
        try:
            output = await execute_tool(block["name"], block["input"])
        except ToolExecutionError as exc:
            write(ui_stream.tool_output_error(block["id"], str(exc)))
            return _tool_result(block["id"], {"erro": str(exc)}, is_error=True)
        except Exception:
            logger.exception("Falha ao executar a tool %s", block["name"])
            write(ui_stream.tool_output_error(block["id"], "Falha na consulta"))
            return _tool_result(block["id"], {"erro": "Falha interna na consulta"}, is_error=True)

        if silent:
            write(ui_stream.data_part("guardrail", {"reason": block["input"].get("motivo", "")}))
        else:
            write(ui_stream.tool_output_available(block["id"], output))
        return _tool_result(block["id"], output)

    # Todos os resultados voltam numa única mensagem user (mantém o Claude fazendo chamadas paralelas)
    results = await asyncio.gather(*(run(block) for block in tool_uses))
    message = {"role": "user", "content": list(results)}
    return {"messages": [message], "history": [message]}


def _tool_result(tool_use_id: str, output: Any, is_error: bool = False) -> dict[str, Any]:
    result = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(output, ensure_ascii=False, default=str),
    }
    if is_error:
        result["is_error"] = True
    return result
