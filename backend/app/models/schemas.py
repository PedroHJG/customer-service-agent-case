"""Contratos com o frontend, espelhando o formato UIMessage do Vercel AI SDK."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class UIMessagePart(BaseModel):
    # Partes de texto, tool (`tool-<nome>`), dados (`data-<nome>`) e `step-start`
    model_config = {"extra": "allow"}

    type: str
    text: str | None = None


class UIMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    parts: list[UIMessagePart]

    def text(self) -> str:
        return "".join(p.text or "" for p in self.parts if p.type == "text").strip()


class ChatRequest(BaseModel):
    """Corpo montado em prepareSendMessagesRequest (frontend/src/hooks/useAgentChat.ts)."""

    chat_id: str = Field(min_length=1, max_length=100)
    message: UIMessage


def ui_message(message_id: str, role: str, parts: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": message_id, "role": role, "parts": parts}
