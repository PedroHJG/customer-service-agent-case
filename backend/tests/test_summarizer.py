import asyncio

from app.agents.summarizer import count_user_turns, render_in_scope, summarize
from tests.test_circuit_breaker import IN_SCOPE_TURN, OFF_TOPIC_TURN


def test_resumo_considera_so_turnos_no_escopo():
    rendered = render_in_scope(OFF_TOPIC_TURN + IN_SCOPE_TURN)

    assert "horário" in rendered
    assert "Das 9h às 18h." in rendered
    assert "bolo" not in rendered
    assert "Só posso ajudar" not in rendered


def test_tool_result_nao_conta_como_turno_do_cliente():
    assert count_user_turns(OFF_TOPIC_TURN + IN_SCOPE_TURN) == 2


def test_conversa_toda_fora_do_escopo_gera_resumo_vazio_sem_chamar_a_api():
    assert asyncio.run(summarize(OFF_TOPIC_TURN)) == ""
