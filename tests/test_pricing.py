import pytest

from margem_real import (
    brl,
    margem_com_markup,
    margem_liquida,
    markup_para_margem,
    preco_minimo,
    preco_sugerido,
)


def test_preco_minimo_conta_manual():
    # 100 / (1 - 0,34) = 151,5151... -> arredonda PARA CIMA: 151,52
    assert preco_minimo(100, 0.34) == 151.52


def test_preco_minimo_com_custo_fixo_exato():
    # (50 + 6) / (1 - 0,36) = 56 / 0,64 = 87,50 exatos
    assert preco_minimo(50, 0.36, custo_fixo=6) == 87.50


def test_preco_sugerido_conta_manual():
    # 100 / (1 - 0,34 - 0,10) = 100 / 0,56 = 178,5714... -> 178,58
    assert preco_sugerido(100, 0.34, 0.10) == 178.58


def test_margem_no_preco_minimo_nao_e_negativa():
    # arredondar para cima garante margem >= 0 no preço mínimo
    for custo in (4.37, 19.9, 100, 333.33, 899.99):
        for d in (0.10, 0.25, 0.36, 0.45):
            p = preco_minimo(custo, d, 6)
            assert margem_liquida(p, custo, d, 6) >= 0


def test_margem_no_preco_sugerido_atinge_alvo():
    for custo in (4.37, 19.9, 100, 333.33):
        for d in (0.10, 0.25, 0.36):
            p = preco_sugerido(custo, d, 0.10, 6)
            assert margem_liquida(p, custo, d, 6) >= 0.10


def test_margem_liquida_valor_conhecido():
    # preço 178,58: (178,58 - 100 - 178,58*0,34) / 178,58 = 17,8628 / 178,58
    # 17,8628 / 178,58 = 0,100027
    assert margem_liquida(178.58, 100, 0.34) == pytest.approx(17.8628 / 178.58, abs=1e-9)


def test_markup_fixo_destroi_margem_em_canal_caro():
    # markup 1,8 sobre custo 100 = preço 180; canal com 36% de despesas + R$ 6 fixo
    m = margem_com_markup(100, 1.8, 0.36, custo_fixo=6)
    assert m == pytest.approx((180 - 100 - 6 - 64.8) / 180)
    assert m < 0.06


def test_markup_para_margem():
    assert markup_para_margem(100, 0.34, 0.10) == 1.79  # 178,58 / 100 = 1,7858 -> 1,79


@pytest.mark.parametrize(
    "args",
    [
        (-1, 0.3),  # custo negativo
        (100, 1.0),  # despesas 100%
        (100, -0.1),  # despesas negativas
        (100, 34),  # percentual passado como inteiro (erro comum)
    ],
)
def test_preco_minimo_rejeita_entradas_invalidas(args):
    with pytest.raises(ValueError):
        preco_minimo(*args)


def test_preco_sugerido_rejeita_margem_impossivel():
    with pytest.raises(ValueError):
        preco_sugerido(100, 0.60, 0.40)  # despesas + margem = 100%


def test_margem_liquida_rejeita_preco_nao_positivo():
    with pytest.raises(ValueError):
        margem_liquida(0, 100, 0.3)


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (1234.5, "R$ 1.234,50"),
        (0, "R$ 0,00"),
        (-9.999, "-R$ 10,00"),
        (1234567.891, "R$ 1.234.567,89"),
    ],
)
def test_brl(valor, esperado):
    assert brl(valor) == esperado
