"""
Orquestração do atendimento com LangGraph:

    START -> agent --(stop_reason == "tool_use")--> tools -> agent ...
                   \--(qualquer outro)-------------> END

Cada conversa é uma thread (thread_id = chat_id do frontend) persistida pelo checkpointer
do Postgres, o que isola o contexto de cada cliente e sobrevive a reinícios do servidor.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.agent_node import agent_node
from app.agents.nodes.tools_node import tools_node
from app.agents.state import AgentState

# Proteção contra loops de tool use (cada volta agent -> tools conta 2 passos)
RECURSION_LIMIT = 16


def _route_after_agent(state: AgentState) -> str:
    return "tools" if state.get("stop_reason") == "tool_use" else END


def build_graph(checkpointer: BaseCheckpointSaver):
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", _route_after_agent, ["tools", END])
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
