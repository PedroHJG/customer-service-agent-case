from decimal import Decimal

from app.services.pricing import brl, max_installments, price_summary


def test_formata_em_reais():
    assert brl(1899.9) == "R$ 1.899,90"
    assert brl(159.9) == "R$ 159,90"


def test_parcelamento_respeita_parcela_minima_por_faixa():
    assert max_installments(Decimal("2199")) == 12  # 183,25 >= 100
    assert max_installments(Decimal("599.9")) == 6  # 7x daria 85,70 (< 100); 6x dá 99,98 (>= 80)
    assert max_installments(Decimal("159.9")) == 3  # 53,30 >= 50
    assert max_installments(Decimal("99")) == 1


def test_pix_tem_5_porcento_de_desconto_sem_promocao():
    assert price_summary(1000, None)["preco_pix"] == "R$ 950,00"


def test_pix_nao_acumula_com_promocao():
    summary = price_summary(1000, 20)
    assert summary["preco_promocional"] == "R$ 800,00"
    assert summary["preco_pix"] == "R$ 800,00"
    assert summary["desconto"] == "20%"
