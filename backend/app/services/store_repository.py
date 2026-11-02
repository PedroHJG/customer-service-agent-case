"""
Consultas às tabelas operacionais (carregadas dos CSVs por scripts/ingest.py).

As tools nunca geram SQL livre: cada consulta é uma função parametrizada, o que evita
SQL injection via prompt e limita o que o agente consegue ler (ex.: dados de outros clientes).

TODO: implementar depois de inspecionar as colunas dos CSVs em data/.
"""


async def search_products(
    query: str | None,
    category: str | None,
    max_price: float | None,
    only_available: bool,
) -> list[dict]:
    raise NotImplementedError("Aguardando os CSVs de produtos/estoque")


async def get_order_status(order_id: str, customer_email: str) -> dict | None:
    raise NotImplementedError("Aguardando os CSVs de pedidos/clientes")


async def list_active_promotions() -> list[dict]:
    raise NotImplementedError("Aguardando o CSV de promoções")
