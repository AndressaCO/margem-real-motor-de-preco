"""Testes de propriedade (Hypothesis): invariantes que valem para QUALQUER entrada válida,
não só para os exemplos escolhidos à mão."""

from decimal import Decimal

import pandas as pd
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from margem_real.agent.evals.metrics import pass_at_k, pass_pow_k
from margem_real.channels import canais_dataframe
from margem_real.pipeline import Armazem, validar_vendas
from margem_real.pricing import margem_liquida, preco_minimo, preco_sugerido

CENTAVO = 0.01
custo_st = st.decimals(min_value="0.01", max_value="5000", places=2).map(float)
fixo_st = st.decimals(min_value="0", max_value="50", places=2).map(float)
desp_st = st.decimals(min_value="0", max_value="0.90", places=2).map(float)
alvo_st = st.decimals(min_value="0", max_value="0.08", places=2).map(float)  # desp+alvo < 1


@given(custo_st, desp_st, fixo_st)
def test_preco_minimo_nunca_da_prejuizo_e_e_o_menor_preco_que_nao_da(c, d, f):
    p = preco_minimo(c, d, f)
    assert margem_liquida(p, c, d, f) >= 0  # o teto ao centavo garante o equilíbrio
    menor = round(p - CENTAVO, 2)
    if menor > 0:
        assert margem_liquida(menor, c, d, f) < 0  # um centavo a menos já dá prejuízo


@given(custo_st, desp_st, alvo_st, fixo_st)
def test_preco_sugerido_entrega_a_margem_alvo_e_e_minimo_para_isso(c, d, m, f):
    p = preco_sugerido(c, d, m, f)
    assert p >= preco_minimo(c, d, f)
    assert margem_liquida(p, c, d, f) >= m - 1e-12
    menor = round(p - CENTAVO, 2)
    if menor > 0:
        assert margem_liquida(menor, c, d, f) < m


@given(custo_st, custo_st, desp_st, fixo_st)
def test_preco_minimo_e_monotono_no_custo(c1, c2, d, f):
    lo, hi = sorted((c1, c2))
    assert preco_minimo(lo, d, f) <= preco_minimo(hi, d, f)


@given(custo_st, desp_st, fixo_st)
def test_resultado_tem_no_maximo_dois_decimais(c, d, f):
    q = Decimal(str(preco_minimo(c, d, f)))
    assert q == q.quantize(Decimal("0.01"))


linha_st = st.fixed_dictionaries(
    {
        "sku": st.sampled_from(["A", "B", "Z", None]),
        "canal": st.sampled_from(["c1", "c2", "zz"]),
        "mes": st.sampled_from(["2026-01", "2026-02", "2026-13", "x"]),
        "unidades": st.one_of(st.integers(-2, 5), st.floats(0, 3, allow_nan=False)),
        "preco": st.one_of(
            st.floats(-5, 50, allow_nan=False), st.just(float("nan")), st.just(float("inf"))
        ),
    }
)


@settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(linha_st, min_size=1, max_size=40))
def test_validacao_particiona_sem_perder_linhas_e_validas_cumprem_as_regras(linhas):
    df = pd.DataFrame(linhas)
    r = validar_vendas(df, {"A", "B"}, {"c1", "c2"})
    assert len(r.validas) + len(r.rejeitadas) == len(df)  # nada some em silêncio
    v = r.validas
    assert v["sku"].isin(["A", "B"]).all() and v["canal"].isin(["c1", "c2"]).all()
    assert (v["unidades"] > 0).all() and (v["unidades"] % 1 == 0).all()
    assert (v["preco"] > 0).all() and v["preco"].map(lambda x: x != float("inf")).all()
    assert not v.duplicated(subset=["sku", "canal", "mes"]).any()
    assert (r.rejeitadas["motivo"] != "").all()


@settings(max_examples=25, deadline=None)
@given(st.randoms(use_true_random=False))
def test_ordem_das_linhas_nao_muda_o_estado_final(rnd):
    base = pd.DataFrame(
        {
            "sku": ["A", "A", "B", "B"],
            "canal": ["c1", "c2", "c1", "c2"],
            "mes": ["2026-01"] * 4,
            "unidades": [1, 2, 3, 4],
            "preco": [10.0, 20.0, 30.0, 40.0],
        }
    )
    idx = list(base.index)
    rnd.shuffle(idx)
    digests = []
    for df in (base, base.loc[idx]):
        a = Armazem()
        a.carregar_canais(canais_dataframe().assign(canal=lambda d: d["canal"]))
        a.con.execute("INSERT INTO canais VALUES ('c1', 0.1, 0), ('c2', 0.1, 0)")
        a.con.execute("INSERT INTO skus VALUES ('A','x',5.0), ('B','x',6.0)")
        a.carregar_vendas(df, queda_max_volume=1.0)
        digests.append(a.impressao_digital())
        a.fechar()
    assert digests[0] == digests[1]


@given(
    st.integers(1, 12).flatmap(
        lambda n: st.tuples(st.just(n), st.integers(0, n), st.integers(1, n))
    )
)
def test_metricas_de_confiabilidade_respeitam_ordem_e_limites(t):
    n, c, k = t
    a, p = pass_at_k(n, c, k), pass_pow_k(n, c, k)
    assert 0 <= p <= a <= 1
    if k == 1:
        assert abs(a - c / n) < 1e-12 and abs(p - c / n) < 1e-12
