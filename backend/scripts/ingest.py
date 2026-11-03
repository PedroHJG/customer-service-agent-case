"""
Carga dos dados da loja no Postgres: `python -m scripts.ingest` (com o docker-compose rodando).

1. Os CSVs são tratados e viram tabelas tipadas (products, orders, ...), com chaves primárias.
2. O PDF de políticas é dividido em trechos por seção, vetorizado e salvo em `policy_chunks` (pgvector).

Idempotente: recria as tabelas a cada execução.
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd
import psycopg
from pgvector.psycopg import register_vector
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import Date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.vector_store import embed  # noqa: E402

settings = get_settings()

PRIMARY_KEYS = {
    "categories": "category_id",
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "promotions": "promotion_id",
}

CHUNK_SIZE = 1200  # caracteres: cabe uma subseção inteira (ex.: 4.1 Direito de Arrependimento)


def read_tables() -> dict[str, pd.DataFrame]:
    # "desafio_tecnico_ai_eng - products.csv" -> "products"
    return {path.stem.split(" - ")[-1].strip(): pd.read_csv(path) for path in settings.data_dir.glob("*.csv")}


def clean(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    for df in tables.values():
        for column in df.select_dtypes(include=["object", "string"]).columns:
            df[column] = df[column].str.strip()

    customers = tables["customers"]
    customers["email"] = customers["email"].str.lower()
    # Só dígitos, para comparar telefones digitados em qualquer formato
    customers["phone_digits"] = customers["phone"].str.replace(r"\D", "", regex=True)

    products = tables["products"]
    products["specs"] = products["specs"].map(json.loads)
    products["created_at"] = pd.to_datetime(products["created_at"]).dt.date

    orders = tables["orders"]
    for column in ("order_date", "estimated_delivery"):
        orders[column] = pd.to_datetime(orders[column]).dt.date

    tables["promotions"]["is_active"] = tables["promotions"]["is_active"].astype(bool)
    return tables


def load_csvs() -> None:
    tables = clean(read_tables())
    engine = create_engine(settings.database_url.replace("postgresql://", "postgresql+psycopg://"))
    dtypes = {
        "products": {"specs": JSONB, "created_at": Date},
        "orders": {"order_date": Date, "estimated_delivery": Date},
    }

    with engine.begin() as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False, dtype=dtypes.get(name))
            if name in PRIMARY_KEYS:
                conn.exec_driver_sql(f"ALTER TABLE {name} ADD PRIMARY KEY ({PRIMARY_KEYS[name]})")
            print(f"  {name}: {len(df)} linhas")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Quebra o manual nos títulos numerados ("4.1 Direito de Arrependimento", "5. Política de Frete")."""
    text = re.sub(r"\s*Página \d+\s*|Empório da Música Manual de Políticas e Procedimentos", "\n", text)
    # Títulos começam na coluna 0; itens de lista numerada (7.2) vêm indentados e não casam
    heading = re.compile(r"^(\d+(?:\.\d+)?\.? [A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{2,80})$", re.MULTILINE)

    parts = heading.split(text)
    sections, current_chapter = [], ""
    for title, body in zip(parts[1::2], parts[2::2]):
        title = title.strip()
        if re.match(r"^\d+\.\s", title):
            current_chapter = title
        label = title if title == current_chapter else f"{current_chapter} > {title}"
        lines = (re.sub(r"\s+", " ", line).strip() for line in body.splitlines())
        body = "\n".join(line for line in lines if line)
        if body:
            sections.append((label, body))
    return sections


def chunk_section(label: str, body: str) -> list[str]:
    # Seções grandes são quebradas por linha; cada trecho carrega o título para dar contexto ao embedding
    chunks, current = [], ""
    for line in body.splitlines():
        if current and len(current) + len(line) > CHUNK_SIZE:
            chunks.append(current)
            current = ""
        current = f"{current}\n{line}".strip()
    if current:
        chunks.append(current)
    return [f"{label}\n{chunk}" for chunk in chunks]


def load_policies() -> None:
    pdf_path = next(settings.data_dir.glob("*.pdf"))
    # O modo padrão do pypdf quebra este PDF em uma palavra por linha; o modo layout preserva as linhas
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)

    rows = [(label, chunk) for label, body in split_sections(text) for chunk in chunk_section(label, body)]
    vectors = embed([content for _, content in rows])

    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS unaccent")  # busca de produtos sem acento
        register_vector(conn)
        conn.execute("DROP TABLE IF EXISTS policy_chunks")
        conn.execute(
            f"""
            CREATE TABLE policy_chunks (
                id SERIAL PRIMARY KEY,
                section TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector({settings.embedding_dim}) NOT NULL,
                -- Índice de texto completo para a parte "palavra-chave" da busca híbrida
                tsv tsvector NOT NULL
            )
            """
        )
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO policy_chunks (section, content, embedding, tsv)
                VALUES (%s, %s, %s, to_tsvector('portuguese', unaccent(%s)))
                """,
                [(section, content, vector, content) for (section, content), vector in zip(rows, vectors)],
            )
    print(f"  {pdf_path.name}: {len(rows)} trechos indexados")


if __name__ == "__main__":
    print("Carregando CSVs...")
    load_csvs()
    print("Indexando políticas...")
    load_policies()
