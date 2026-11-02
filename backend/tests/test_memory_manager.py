import json

from app.controllers.memory_manager import to_ui_messages


def test_converte_turno_com_tool_e_guardrail_em_uimessages():
    history = [
        {"role": "user", "content": "Quanto custa o Takamine GD20?"},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "", "signature": "sig"},
                {"type": "tool_use", "id": "tu_1", "name": "buscar_produtos", "input": {"termo": "Takamine GD20"}},
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": json.dumps({"preco": 1899.9})}],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "Sai por R$ 1.899,90!"}]},
        {"role": "user", "content": "Me passa uma receita de bolo"},
        {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "tu_2", "name": "registrar_fora_de_escopo", "input": {"motivo": "receita"}},
            ],
        },
    ]

    messages = to_ui_messages("chat", history)

    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    first_answer = [p for p in messages[1]["parts"] if p["type"] != "step-start"]
    assert first_answer[0] == {
        "type": "tool-buscar_produtos",
        "toolCallId": "tu_1",
        "state": "output-available",
        "input": {"termo": "Takamine GD20"},
        "output": {"preco": 1899.9},
    }
    assert first_answer[1]["text"] == "Sai por R$ 1.899,90!"
    assert {"type": "data-guardrail", "data": {"reason": "receita"}} in messages[3]["parts"]


def test_ignora_blocos_internos_anteriores_a_um_fallback():
    history = [
        {"role": "user", "content": "Oi"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Olá"},
                {"type": "tool_use", "id": "tu_x", "name": "buscar_produtos", "input": {}},
                {"type": "fallback", "from": {"model": "a"}, "to": {"model": "b"}},
                {"type": "text", "text": "! Como posso ajudar?"},
            ],
        },
    ]

    parts = to_ui_messages("chat", history)[1]["parts"]

    assert [p["type"] for p in parts] == ["step-start", "text", "text"]
