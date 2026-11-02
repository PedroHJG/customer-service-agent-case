from fastapi import APIRouter

from app.views import chat_router

api_router = APIRouter()
api_router.include_router(chat_router.router, tags=["chat"])


@api_router.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok"}
