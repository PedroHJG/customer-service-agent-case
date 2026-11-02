"""
Camada de compatibilidade com o frontend: protocolo "UI Message Stream" do Vercel AI SDK.

O useChat do frontend consome Server-Sent Events onde cada evento é um JSON com `type`
(text-delta, tool-input-available, tool-output-available, data-*, ...). Os nós do LangGraph
emitem esses dicts via `get_stream_writer()` e aqui eles viram linhas SSE.
Referência: node_modules/ai/docs/04-ai-sdk-ui/50-stream-protocol.mdx (frontend).
"""

import json
from typing import Any

# Header obrigatório para o useChat reconhecer o protocolo
UI_STREAM_HEADERS = {
    "x-vercel-ai-ui-message-stream": "v1",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

UIEvent = dict[str, Any]


def sse(event: UIEvent) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


SSE_DONE = "data: [DONE]\n\n"


def start(message_id: str) -> UIEvent:
    return {"type": "start", "messageId": message_id}


def finish() -> UIEvent:
    return {"type": "finish"}


def start_step() -> UIEvent:
    return {"type": "start-step"}


def finish_step() -> UIEvent:
    return {"type": "finish-step"}


def text_start(block_id: str) -> UIEvent:
    return {"type": "text-start", "id": block_id}


def text_delta(block_id: str, delta: str) -> UIEvent:
    return {"type": "text-delta", "id": block_id, "delta": delta}


def text_end(block_id: str) -> UIEvent:
    return {"type": "text-end", "id": block_id}


def tool_input_start(tool_call_id: str, tool_name: str) -> UIEvent:
    return {"type": "tool-input-start", "toolCallId": tool_call_id, "toolName": tool_name}


def tool_input_available(tool_call_id: str, tool_name: str, tool_input: Any) -> UIEvent:
    return {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input}


def tool_output_available(tool_call_id: str, output: Any) -> UIEvent:
    return {"type": "tool-output-available", "toolCallId": tool_call_id, "output": output}


def tool_output_error(tool_call_id: str, error_text: str) -> UIEvent:
    return {"type": "tool-output-error", "toolCallId": tool_call_id, "errorText": error_text}


def data_part(name: str, data: Any) -> UIEvent:
    """Parte customizada `data-<name>` (o frontend tipa em AgentDataParts)."""
    return {"type": f"data-{name}", "data": data}


def error(error_text: str) -> UIEvent:
    return {"type": "error", "errorText": error_text}
