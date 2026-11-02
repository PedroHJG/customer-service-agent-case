from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

# Um único pool compartilhado: consultas das tools, busca vetorial e checkpointer do LangGraph
pool = AsyncConnectionPool(
    conninfo=get_settings().database_url,
    # autocommit + prepare_threshold=0 são exigidos pelo AsyncPostgresSaver
    kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    open=False,
)
