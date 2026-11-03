import operator
from typing import Annotated, Any, Literal, TypedDict

Message = dict[str, Any]


def transcript_reducer(current: list[Message] | None, update: list[Message] | dict) -> list[Message]:
    """
    Append-only, exceto na compactação: `{"replace": [...]}` troca o transcript inteiro pelo resumo.
    Nunca removemos turnos do meio: o Opus 5.5 rejeita (400) histórico editado com thinking replayado.
    """
    if isinstance(update, dict) and "replace" in update:
        return list(update["replace"])
    return (current or []) + update


class AgentState(TypedDict, total=False):
    # Mensagem do cliente desta rodada (já com cabeçalho de data/hora); sobrescrita a cada invocação
    incoming: str
    # Transcript enviado ao Claude (formato Messages API). Turnos com resposta padrão nunca entram aqui
    messages: Annotated[list[Message], transcript_reducer]
    # Tudo o que aconteceu na conversa, só para a UI redesenhar o histórico
    history: Annotated[list[Message], operator.add]
    # Índice em `messages` onde começa o turno atual (para saber se ele acionou o guardrail)
    turn_start: int
    route: Literal["agent", "circuit_open"]
    # stop_reason da última resposta do Claude: decide se o grafo vai para as tools ou finaliza o turno
    stop_reason: str | None
    # Circuit breaker: mensagens seguidas fora do escopo e se o atendimento automático está pausado
    off_topic_streak: int
    breaker_open: bool
