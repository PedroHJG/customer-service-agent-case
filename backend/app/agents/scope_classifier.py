"""
Classificador de escopo barato (Haiku), usado só com o circuit breaker aberto: decide se o cliente
voltou a falar de assuntos da loja sem gastar uma chamada do modelo principal.
"""

import logging

import anthropic
from pydantic import BaseModel

from app.agents.prompts import SCOPE_CLASSIFIER_PROMPT
from app.core.config import get_settings
from app.services.llm_service import client

logger = logging.getLogger(__name__)


class ScopeDecision(BaseModel):
    dentro_do_escopo: bool


async def is_in_scope(text: str) -> bool:
    try:
        response = await client.messages.parse(
            model=get_settings().auxiliary_model,
            max_tokens=1024,
            system=SCOPE_CLASSIFIER_PROMPT,
            messages=[{"role": "user", "content": f"<mensagem>\n{text}\n</mensagem>"}],
            output_format=ScopeDecision,
        )
    except anthropic.APIError:
        # Falha no classificador não pode travar o cliente: deixa o modelo principal decidir
        logger.exception("Falha no classificador de escopo; tratando como dentro do escopo")
        return True

    if response.stop_reason == "refusal" or response.parsed_output is None:
        return False
    return response.parsed_output.dentro_do_escopo
