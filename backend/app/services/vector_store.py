"""Busca semântica no manual de políticas (chunks do PDF com embeddings no pgvector)."""

import asyncio
from functools import lru_cache

from fastembed import TextEmbedding
from pgvector.psycopg import register_vector_async

from app.core.config import get_settings
from app.core.database import pool

settings = get_settings()


@lru_cache
def _embedder() -> TextEmbedding:
    # Modelo local (ONNX/CPU), multilíngue e leve (~220 MB): sem custo nem chave de API extra
    return TextEmbedding(settings.embedding_model, cache_dir=str(settings.data_dir.parent / ".cache"))


def embed(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _embedder().embed(texts)]


async def search_policies(query: str, top_k: int = 4) -> list[dict]:
    [query_vector] = await asyncio.to_thread(embed, [query])

    async with pool.connection() as conn:
        await register_vector_async(conn)
        cursor = await conn.execute(
            """
            SELECT section, content, 1 - (embedding <=> %s::vector) AS score
            FROM policy_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_vector, query_vector, top_k),
        )
        rows = await cursor.fetchall()

    return [{"secao": r["section"], "trecho": r["content"], "relevancia": round(r["score"], 3)} for r in rows]
