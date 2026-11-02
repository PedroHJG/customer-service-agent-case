import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    # Histórico no formato da Messages API da Anthropic (append-only: cada nó só acrescenta).
    # Persistido pelo checkpointer do Postgres com thread_id = chat_id.
    messages: Annotated[list[dict[str, Any]], operator.add]
    # stop_reason da última resposta do Claude: decide se o grafo vai para as tools ou termina
    stop_reason: str | None
