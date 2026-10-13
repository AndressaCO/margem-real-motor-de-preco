import pandas as pd
import pytest

from margem_real.analysis import (
    abaixo_do_minimo,
    margem_por_sku_canal,
    repricing,
    resumo_por_canal,
)
from margem_real.channels import CANAIS_ILUSTRATIVOS, canais_dataframe
from margem_real.cli import construir_relatorio
from margem_real.pricing import margem_liquida, preco_minimo
from margem_real.synthetic import gerar_skus, gerar_vendas


@pytest.fixture(scope="module")
def dados():
    skus = gerar_skus(60, semente=7)
    canais = canais_dataframe()
    vendas = gerar_vendas(skus, semente=7)
    return skus, canais, vendas, margem_por_sku_canal(vendas, skus, canais)


def test_dados_sao_reprodutiveis():
    a = gerar_vendas(gerar_skus(30, 1), semente=1)
    b = gerar_vendas(gerar_skus(30, 1), semente=1)
    pd.testing.assert_frame_equal(a, b)


def test_sql_fecha_com_receita_e_unidades(dados):
    _, _, vendas, margem = dados
    assert margem["receita"].sum() == pytest.approx((vendas.unidades * vendas.preco).sum(), abs=0.5)
    assert margem["unidades"].sum() == vendas["unidades"].sum()


def test_identidade_contabil_da_margem(dados):
    # receita - cmv - despesas = margem de contribuição, linha a linha
    _, _, _, m = dados
    recomposta = m["receita"] - m["cmv"] - m["despesas_variaveis"]
    assert (recomposta - m["margem_contribuicao"]).abs().max() < 0.02


def test_sql_confere_com_python(dados):
    # Duas implementações independentes (SQL e pricing.py) devem concordar.
    skus, _, vendas, m = dados
    por_canal = {c.nome: c for c in CANAIS_ILUSTRATIVOS}
    for r in m.head(40).itertuples(index=False):
        c = por_canal[r.canal]
        py = preco_minimo(r.custo, c.despesas_sobre_preco, c.custo_fixo)
        assert r.preco_minimo == pytest.approx(py, abs=0.011)
        margem_py = margem_liquida(
            r.preco_medio_praticado, r.custo, c.despesas_sobre_preco, c.custo_fixo
        )
        assert r.margem_pct == pytest.approx(margem_py, abs=0.002)


def test_abaixo_do_minimo_coincide_com_margem_negativa(dados):
    _, _, _, m = dados
    prej = abaixo_do_minimo(m)
    assert (prej["margem_contribuicao"] < 0.01).all()


def test_repricing_entrega_margem_alvo(dados):
    _, canais, _, m = dados
    novo = repricing(m, canais, 0.10)
    por_canal = {c.nome: c for c in CANAIS_ILUSTRATIVOS}
    for r in novo.head(40).itertuples(index=False):
        c = por_canal[r.canal]
        m_ = margem_liquida(r.preco_sugerido, r.custo, c.despesas_sobre_preco, c.custo_fixo)
        assert m_ >= 0.10


def test_resumo_por_canal_soma(dados):
    _, _, _, m = dados
    r = resumo_por_canal(m)
    assert r["receita"].sum() == pytest.approx(m["receita"].sum())
    assert r["pares"].sum() == len(m)


def test_relatorio_roda_e_declara_dados_sinteticos():
    texto, _ = construir_relatorio(40, 1.8, 0.10, 3)
    assert "sintéticos" in texto
    assert "R$" in texto
