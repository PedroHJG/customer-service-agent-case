"""
Regras comerciais do manual (seções 3 e 6) calculadas em código, não pelo LLM:
contas feitas pelo modelo podem errar, e preço errado pode configurar propaganda enganosa (7.1).
"""

from decimal import ROUND_HALF_UP, Decimal

PIX_DISCOUNT = Decimal("0.05")
MAX_INSTALLMENTS = 12


def brl(value: Decimal | float) -> str:
    """1899.9 -> 'R$ 1.899,90'"""
    text = f"{Decimal(str(value)).quantize(Decimal('0.01'), ROUND_HALF_UP):,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def _min_installment(installments: int) -> Decimal:
    # 3.1: até 3x sem mínimo (mas nunca abaixo de R$ 50,00); 4x-6x mínimo R$ 80,00; 7x-12x mínimo R$ 100,00
    if installments >= 7:
        return Decimal("100")
    if installments >= 4:
        return Decimal("80")
    return Decimal("50")


def max_installments(price: Decimal) -> int:
    for installments in range(MAX_INSTALLMENTS, 1, -1):
        if price / installments >= _min_installment(installments):
            return installments
    return 1


def price_summary(price: float, promo_percent: int | None) -> dict:
    """Preço de tabela, promoção vigente, preço no PIX e parcelamento máximo sem juros."""
    list_price = Decimal(str(price))
    summary: dict = {"preco_tabela": brl(list_price)}

    if promo_percent:
        final_price = list_price * (100 - promo_percent) / 100
        summary["preco_promocional"] = brl(final_price)
        summary["desconto"] = f"{promo_percent}%"
        # 6.2: promoções não são cumulativas, o desconto do PIX não se aplica sobre preço promocional
        summary["preco_pix"] = brl(final_price)
    else:
        final_price = list_price
        summary["preco_pix"] = brl(list_price * (1 - PIX_DISCOUNT))

    installments = max_installments(final_price)
    if installments > 1:
        summary["parcelamento"] = f"até {installments}x de {brl(final_price / installments)} sem juros"
    return summary
