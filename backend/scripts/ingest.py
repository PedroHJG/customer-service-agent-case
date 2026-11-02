"""
Carga dos dados da loja no Postgres: `python -m scripts.ingest` (com o docker-compose rodando).

1. Cada data/*.csv vira uma tabela com o mesmo nome do arquivo.
2. O PDF de políticas é dividido em trechos, vetorizado e salvo em `policy_chunks` (pgvector).

Idempotente: recria as tabelas a cada execução.
"""

import re
import sys
from pathlib import Path

import pandas as pd
import psycopg
from pgvector.psycopg import register_vector
from pypdf import PdfReader
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.vector_store import embed  # noqa: E402

settings = get_settings()

CHUNK_SIZE = 900  # caracteres por trecho: cabe uma regra completa sem misturar muitos assuntos
CHUNK_OVERLAP = 150


def load_csvs() -> None:
    engine = create_engine(settings.database_url.replace("postgresql://", "postgresql+psycopg://"))
    for csv_path in sorted(settings.data_dir.glob("*.csv")):
        df = pd.read_csv(csv_path)
        # TODO: tratamento específico por tabela (tipos, datas, normalização de texto) após ver os dados
        df.to_sql(csv_path.stem, engine, if_exists="replace", index=False)
        print(f"  {csv_path.stem}: {len(df)} linhas")


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) > CHUNK_SIZE:
            chunks.append(current)
            current = current[-CHUNK_OVERLAP:]
        current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks


def load_policies() -> None:
    pdf_path = next(settings.data_dir.glob("*.pdf"))
    reader = PdfReader(pdf_path)

    rows = []
    for page_number, page in enumerate(reader.pages, start=1):
        for chunk in chunk_text(page.extract_text() or ""):
            rows.append((f"Página {page_number}", chunk))

    vectors = embed([content for _, content in rows])

    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        conn.execute("DROP TABLE IF EXISTS policy_chunks")
        conn.execute(
            f"""
            CREATE TABLE policy_chunks (
                id SERIAL PRIMARY KEY,
                section TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector({settings.embedding_dim}) NOT NULL
            )
            """
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO policy_chunks (section, content, embedding) VALUES (%s, %s, %s)",
                [(section, content, vector) for (section, content), vector in zip(rows, vectors)],
            )
    print(f"  {pdf_path.name}: {len(rows)} trechos indexados")


if __name__ == "__main__":
    print("Carregando CSVs...")
    load_csvs()
    print("Indexando políticas...")
    load_policies()
