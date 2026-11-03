"""
Busca no manual de políticas (chunks do PDF no Postgres): híbrida, vetorial + texto completo.

Só o vetor (modelo pequeno, multilíngue) falha em perguntas literais: "endereço da loja" não trazia a
seção 1.2 Dados da Empresa. Só palavra-chave falha em paráfrases. A parte de palavra-chave pondera
cada termo pelo IDF (como no BM25), e as duas listas são combinadas por Reciprocal Rank Fusion,
que usa só a posição em cada ranking e dispensa calibrar as escalas. Com ~25 trechos a varredura
completa é instantânea; num manual grande valeria um índice GIN/BM25 dedicado.
"""

import asyncio
from functools import lru_cache

from fastembed import TextEmbedding
from pgvector.psycopg import register_vector_async

from app.core.config import get_settings
from app.core.database import pool

settings = get_settings()

RRF_K = 60  # constante usual do RRF: suaviza a diferença entre as primeiras posições
CANDIDATES = 20


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
            WITH terms AS (
                SELECT DISTINCT unnest(tsvector_to_array(to_tsvector('portuguese', unaccent(%(text)s)))) AS term
            ),
            idf AS (
                -- Termo raro pesa mais: "endereço" (1 seção) vale mais que "loja" (quase todas)
                SELECT t.term, ln((SELECT count(*) FROM policy_chunks)::numeric / count(*)) AS weight
                FROM terms t JOIN policy_chunks c ON t.term = ANY (tsvector_to_array(c.tsv))
                GROUP BY t.term
            ),
            semantic AS (
                SELECT id, row_number() OVER (ORDER BY embedding <=> %(vector)s::vector) AS rank
                FROM policy_chunks
                ORDER BY embedding <=> %(vector)s::vector
                LIMIT %(candidates)s
            ),
            keyword AS (
                SELECT c.id, row_number() OVER (ORDER BY sum(idf.weight) DESC) AS rank
                FROM policy_chunks c JOIN idf ON idf.term = ANY (tsvector_to_array(c.tsv))
                WHERE idf.weight > 0
                GROUP BY c.id
                ORDER BY rank
                LIMIT %(candidates)s
            )
            SELECT c.section, c.content,
                   COALESCE(1.0 / (%(rrf_k)s + s.rank), 0) + COALESCE(1.0 / (%(rrf_k)s + k.rank), 0) AS score
            FROM policy_chunks c
            LEFT JOIN semantic s USING (id)
            LEFT JOIN keyword k USING (id)
            WHERE s.id IS NOT NULL OR k.id IS NOT NULL
            ORDER BY score DESC
            LIMIT %(top_k)s
            """,
            {"text": query, "vector": query_vector, "candidates": CANDIDATES, "rrf_k": RRF_K, "top_k": top_k},
        )
        rows = await cursor.fetchall()

    # O conteúdo começa com o título da seção (útil no embedding); na resposta ele já vai em "secao"
    return [{"secao": r["section"], "trecho": r["content"].split("\n", 1)[-1]} for r in rows]
