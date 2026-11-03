"""
Resumo do histórico (compactação "simples"): o transcript inteiro vira um único resumo, feito só com os
turnos dentro do escopo. Turnos em que o agente acionou o guardrail ficam de fora.

Por que trocar o histórico todo em vez de manter os últimos turnos: o Opus 5.5 rejeita thinking blocks
replayados depois de qualquer edição no prefixo, então "resumo + cauda verbatim" quebraria. O formato
resumo + nova mensagem é o recomendado pela Anthropic e não reaproveita thinking antigo.
"""

import json
import logging
from typing import Any

import anthropic

from app.agents.prompts import SUMMARY_PROMPT
from app.agents.tools import TOOLS
from app.core.config import get_settings
from app.services.llm_service import client, visible_blocks

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 1500


def split_turns(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Um turno começa em cada mensagem de texto do cliente (tool_result também tem role user)."""
    turns: list[list[dict[str, Any]]] = []
    for message in messages:
        if message["role"] == "user" and isinstance(message["content"], str):
            turns.append([])
        if turns:
            turns[-1].append(message)
    return turns


def is_off_topic(turn: list[dict[str, Any]]) -> bool:
    return any(
        block["type"] == "tool_use" and block["name"] in TOOLS and TOOLS[block["name"]].silent
        for message in turn
        if message["role"] == "assistant"
        for block in visible_blocks(message["content"])
    )


def count_user_turns(messages: list[dict[str, Any]]) -> int:
    return len(split_turns(messages))


def render_in_scope(messages: list[dict[str, Any]]) -> str:
    """Transcript legível dos turnos no escopo, com o que as ferramentas retornaram (fatos a preservar)."""
    lines: list[str] = []
    for turn in split_turns(messages):
        if is_off_topic(turn):
            continue
        for message in turn:
            content = message["content"]
            if isinstance(content, str):
                lines.append(f"Cliente: {content}")
                continue
            for block in visible_blocks(content) if message["role"] == "assistant" else content:
                if block["type"] == "text":
                    lines.append(f"Atendente: {block['text']}")
                elif block["type"] == "tool_use":
                    lines.append(f"[consulta {block['name']} {json.dumps(block['input'], ensure_ascii=False)}]")
                elif block["type"] == "tool_result":
                    lines.append(f"[resultado {block['content'][:MAX_TOOL_RESULT_CHARS]}]")
        lines.append("")
    return "\n".join(lines).strip()


async def summarize(messages: list[dict[str, Any]]) -> str | None:
    """Resumo dos turnos no escopo; "" se não houver nenhum; None se o resumo falhar (não compacta)."""
    transcript = render_in_scope(messages)
    if not transcript:
        return ""

    try:
        response = await client.messages.create(
            model=get_settings().auxiliary_model,
            max_tokens=4096,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": f"<conversa>\n{transcript}\n</conversa>"}],
        )
    except anthropic.APIError:
        logger.exception("Falha ao resumir o histórico; mantendo o transcript completo")
        return None

    if response.stop_reason == "refusal":
        return None
    return "".join(block.text for block in response.content if block.type == "text").strip() or None
