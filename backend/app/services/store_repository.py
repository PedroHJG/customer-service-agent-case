"""
Consultas às tabelas operacionais (carregadas dos CSVs por scripts/ingest.py).

As tools nunca geram SQL livre: cada consulta é uma função parametrizada, o que evita
SQL injection via prompt e limita o que o agente consegue ler (ex.: dados de outros clientes).
"""

import re
from typing import Any

from app.core.clock import now_local
from app.core.database import pool
from app.services.pricing import brl, price_summary

MAX_PRODUCTS = 10

# Normaliza texto para busca: minúsculas, sem acento e sem pontuação ("GD-20" casa com "gd20")
_NORMALIZED = "regexp_replace(unaccent(lower({})), '[^a-z0-9 ]', '', 'g')"

ORDER_STATUS = {
    "pending": "aguardando confirmação do pagamento",
    "confirmed": "pagamento confirmado, pedido em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}


def _payment_label(method: str) -> str:
    if match := re.fullmatch(r"credit_(\d+)x", method):
        return f"cartão de crédito em {match.group(1)}x"
    return {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto bancário"}.get(method, method)


def _availability(status: str, stock: int) -> str:
    # O status prevalece sobre o estoque: há produto descontinuado com estoque > 0 nos dados
    if status == "discontinued":
        return "descontinuado (não faz mais parte do catálogo)"
    if status == "coming_soon":
        return "em breve (ainda não disponível para venda)"
    return f"disponível ({stock} em estoque)" if stock > 0 else "esgotado no momento"


def _normalize_term(term: str) -> list[str]:
    cleaned = re.sub(r"[^\w ]", "", term.lower())
    return [token for token in cleaned.split() if len(token) > 1]


async def search_products(
    query: str | None,
    category: str | None,
    max_price: float | None,
    only_available: bool,
) -> list[dict[str, Any]]:
    conditions, params = [], {"category": category, "max_price": max_price, "limit": MAX_PRODUCTS}

    # Cada palavra do termo precisa aparecer no nome, categoria, descrição ou especificações
    searchable = _NORMALIZED.format("p.name || ' ' || c.name || ' ' || p.description || ' ' || p.specs::text")
    for i, token in enumerate(_normalize_term(query or "")):
        conditions.append(f"{searchable} LIKE '%%' || {_NORMALIZED.format(f'%(t{i})s')} || '%%'")
        params[f"t{i}"] = token

    if only_available:
        conditions.append("p.status = 'active' AND p.stock_quantity > 0")

    where = " AND ".join(["TRUE", *conditions])
    sql = f"""
        SELECT p.product_id, p.name, c.name AS category, p.description, p.price_brl, p.stock_quantity,
               p.status, p.specs, pr.discount_percent, pr.description AS campaign
        FROM products p
        JOIN categories c USING (category_id)
        LEFT JOIN promotions pr ON pr.product_id = p.product_id AND pr.is_active
        WHERE {where}
          AND (%(category)s::text IS NULL OR c.name = %(category)s)
          AND (%(max_price)s::numeric IS NULL
               OR p.price_brl * (100 - COALESCE(pr.discount_percent, 0)) / 100 <= %(max_price)s)
        ORDER BY p.price_brl * (100 - COALESCE(pr.discount_percent, 0)) / 100
        LIMIT %(limit)s
    """

    async with pool.connection() as conn:
        rows = await (await conn.execute(sql, params)).fetchall()

    products = []
    for row in rows:
        product = {
            "nome": row["name"],
            "categoria": row["category"],
            "disponibilidade": _availability(row["status"], row["stock_quantity"]),
            "descricao": row["description"],
            "especificacoes": row["specs"],
        }
        # Produto fora de linha ou ainda não lançado não tem preço de venda a informar
        if row["status"] == "active":
            product.update(price_summary(row["price_brl"], row["discount_percent"]))
            if row["campaign"]:
                product["campanha"] = row["campaign"]
        products.append(product)
    return products


async def get_order_status(order_number: str, customer_identifier: str) -> dict[str, Any] | None:
    """Só retorna o pedido se o e-mail ou telefone informado for do dono do pedido."""
    if not order_number.strip().lstrip("#").isdigit():
        return None
    order_id = int(order_number.strip().lstrip("#"))
    email = customer_identifier.strip().lower()
    phone = re.sub(r"\D", "", customer_identifier)

    async with pool.connection() as conn:
        order = await (
            await conn.execute(
                """
                SELECT o.*, c.name AS customer_name
                FROM orders o JOIN customers c USING (customer_id)
                WHERE o.order_id = %s AND (c.email = %s OR (length(%s) >= 8 AND c.phone_digits LIKE '%%' || %s))
                """,
                (order_id, email, phone, phone),
            )
        ).fetchone()
        if order is None:
            return None
        items = await (
            await conn.execute(
                """
                SELECT p.name, oi.quantity
                FROM order_items oi JOIN products p USING (product_id)
                WHERE oi.order_id = %s
                """,
                (order_id,),
            )
        ).fetchall()

    today = now_local().date()
    result: dict[str, Any] = {
        "numero_pedido": order["order_id"],
        "primeiro_nome_cliente": order["customer_name"].split()[0],
        "status": ORDER_STATUS.get(order["status"], order["status"]),
        "data_compra": order["order_date"].strftime("%d/%m/%Y"),
        "dias_desde_a_compra": (today - order["order_date"]).days,
        # total_brl é o valor cobrado (em 2 pedidos difere da soma dos itens, possivelmente por desconto)
        "valor_total": brl(order["total_brl"]),
        "forma_pagamento": _payment_label(order["payment_method"]),
        "itens": [f"{item['quantity']}x {item['name']}" for item in items],
    }
    if order["tracking_code"]:
        result["codigo_rastreio"] = order["tracking_code"]
    if order["estimated_delivery"]:
        result["data_entrega_prevista"] = order["estimated_delivery"].strftime("%d/%m/%Y")
        if order["status"] == "delivered":
            # Não há data real de entrega nos dados: a prevista é usada como aproximação do recebimento
            result["dias_desde_a_entrega_aprox"] = (today - order["estimated_delivery"]).days
    if order["notes"]:
        result["observacao"] = order["notes"]
    return result


async def list_active_promotions() -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT p.name, c.name AS category, p.price_brl, p.stock_quantity, p.status,
                       pr.discount_percent, pr.description AS campaign
                FROM promotions pr
                JOIN products p USING (product_id)
                JOIN categories c USING (category_id)
                WHERE pr.is_active
                ORDER BY pr.discount_percent DESC
                """
            )
        ).fetchall()

    return [
        {
            "nome": row["name"],
            "categoria": row["category"],
            "campanha": row["campaign"],
            "disponibilidade": _availability(row["status"], row["stock_quantity"]),
            **price_summary(row["price_brl"], row["discount_percent"]),
        }
        for row in rows
    ]
