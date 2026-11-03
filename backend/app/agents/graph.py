"""
Orquestração do atendimento com LangGraph:

    START -> entry --(breaker aberto e fora do escopo)--> circuit_breaker -> END
                  \--(demais casos)--> agent --(tool_use)--> tools -> agent ...
                                             \--(fim)-----> finalize -> END

- entry: classifica a mensagem com o modelo barato quando o breaker está aberto e compacta o histórico.
- finalize: conta mensagens seguidas fora do escopo e abre o breaker ao atingir o limite.

Cada conversa é uma thread (thread_id = chat_id do frontend) persistida pelo checkpointer
do Postgres, o que isola o contexto de cada cliente e sobrevive a reinícios do servidor.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.agent_node import agent_node
from app.agents.nodes.circuit_breaker_node import circuit_breaker_node
from app.agents.nodes.entry_node import entry_node
from app.agents.nodes.finalize_node import finalize_node
from app.agents.nodes.tools_node import tools_node
from app.agents.state import AgentState

# Proteção contra loops de tool use (cada volta agent -> tools conta 2 passos)
RECURSION_LIMIT = 20


def _route_after_entry(state: AgentState) -> str:
    return "circuit_breaker" if state.get("route") == "circuit_open" else "agent"


def _route_after_agent(state: AgentState) -> str:
    return "tools" if state.get("stop_reason") == "tool_use" else "finalize"


def build_graph(checkpointer: BaseCheckpointSaver):
    graph = StateGraph(AgentState)
    graph.add_node("entry", entry_node)
    graph.add_node("circuit_breaker", circuit_breaker_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "entry")
    graph.add_conditional_edges("entry", _route_after_entry, ["circuit_breaker", "agent"])
    graph.add_edge("circuit_breaker", END)
    graph.add_conditional_edges("agent", _route_after_agent, ["tools", "finalize"])
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)
