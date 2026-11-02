from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.controllers import chat_controller, memory_manager
from app.core.config import get_settings
from app.models.schemas import ChatRequest
from app.services.ui_stream import UI_STREAM_HEADERS

router = APIRouter()
settings = get_settings()


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    text = body.message.text()
    if not text:
        raise HTTPException(422, "Mensagem vazia")
    if len(text) > settings.max_user_message_chars:
        raise HTTPException(422, f"Mensagem acima de {settings.max_user_message_chars} caracteres")

    return StreamingResponse(
        chat_controller.stream_chat(request.app.state.graph, body.chat_id, text),
        media_type="text/event-stream",
        headers=UI_STREAM_HEADERS,
    )


@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: str, request: Request) -> list[dict]:
    return await memory_manager.get_history(request.app.state.graph, chat_id)


@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, request: Request) -> Response:
    await memory_manager.delete_history(request.app.state.checkpointer, chat_id)
    return Response(status_code=204)
