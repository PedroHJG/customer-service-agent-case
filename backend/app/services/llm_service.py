from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings

settings = get_settings()

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

# Se um classificador de segurança recusar a resposta, a própria API refaz a chamada
# no modelo de fallback recomendado (evita que um falso positivo derrube o atendimento).
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def request_params() -> dict[str, Any]:
    """Parâmetros fixos de toda chamada ao Claude (os variáveis entram no nó do agente)."""
    return {
        "model": settings.claude_model,
        "max_tokens": settings.claude_max_tokens,
        # Opus 5.5 sempre pensa (adaptive); a profundidade é controlada pelo effort
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": settings.claude_effort},
        # Cacheia automaticamente o prefixo estável (tools + system + histórico)
        "cache_control": {"type": "ephemeral"},
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
    }


def visible_blocks(content: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Após um fallback no meio da resposta, blocos internos (thinking, tool_use) anteriores ao
    último bloco `fallback` pertencem à tentativa recusada e não devem ser reenviados nem executados.
    """
    last_fallback = max((i for i, b in enumerate(content) if b["type"] == "fallback"), default=-1)
    if last_fallback == -1:
        return content
    before = [b for b in content[:last_fallback] if b["type"] == "text"]
    return before + content[last_fallback + 1 :]
