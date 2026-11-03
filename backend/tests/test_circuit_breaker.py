import pytest

from app.agents.nodes.finalize_node import finalize_node
from app.agents.state import transcript_reducer
from app.core.config import get_settings

OFF_TOPIC_TURN = [
    {"role": "user", "content": "me passa uma receita de bolo"},
    {
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "t1", "name": "registrar_fora_de_escopo", "input": {"motivo": "receita"}}],
    },
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]},
    {"role": "assistant", "content": [{"type": "text", "text": "Só posso ajudar com assuntos da loja."}]},
]
IN_SCOPE_TURN = [
    {"role": "user", "content": "qual o horário de vocês?"},
    {"role": "assistant", "content": [{"type": "text", "text": "Das 9h às 18h."}]},
]


@pytest.fixture(autouse=True)
def threshold(monkeypatch):
    monkeypatch.setenv("OUT_OF_SCOPE_THRESHOLD", "3")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_conta_mensagens_seguidas_fora_do_escopo():
    assert finalize_node({"messages": OFF_TOPIC_TURN, "turn_start": 0, "off_topic_streak": 0}) == {
        "off_topic_streak": 1,
        "breaker_open": False,
    }


def test_abre_o_breaker_ao_atingir_o_limite():
    result = finalize_node({"messages": OFF_TOPIC_TURN, "turn_start": 0, "off_topic_streak": 2})
    assert result == {"off_topic_streak": 3, "breaker_open": True}


def test_mensagem_no_escopo_zera_o_contador():
    state = {"messages": OFF_TOPIC_TURN + IN_SCOPE_TURN, "turn_start": len(OFF_TOPIC_TURN), "off_topic_streak": 2}
    assert finalize_node(state) == {"off_topic_streak": 0}


def test_transcript_e_append_only_exceto_na_compactacao():
    current = [{"role": "user", "content": "a"}]
    assert transcript_reducer(current, [{"role": "user", "content": "b"}]) == current + [{"role": "user", "content": "b"}]
    assert transcript_reducer(current, {"replace": [{"role": "user", "content": "resumo"}]}) == [
        {"role": "user", "content": "resumo"}
    ]
