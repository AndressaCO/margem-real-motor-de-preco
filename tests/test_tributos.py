from fractions import Fraction

import pytest

from margem_real.channels import CANAIS_ILUSTRATIVOS, com_simples
from margem_real.cli import construir_relatorio
from margem_real.tributos import FAIXAS_ANEXO_I, aliquota_efetiva_simples_anexo1


@pytest.mark.parametrize(
    "rbt12,conta,exato",
    [
        # contas de mão: (RBT12 x nominal - deduzir) / RBT12, valores EXATOS (sem arredondar)
        (500_000, Fraction(500_000 * 950 - 13_860 * 10_000, 500_000 * 10_000), "0.06728"),
        (1_000_000, Fraction(1_000_000 * 1070 - 22_500 * 10_000, 1_000_000 * 10_000), "0.0845"),
        (1_800_000, Fraction(1_800_000 * 1070 - 22_500 * 10_000, 1_800_000 * 10_000), "0.0945"),
        (3_600_000, Fraction(3_600_000 * 1430 - 87_300 * 10_000, 3_600_000 * 10_000), "0.11875"),
        (4_800_000, Fraction(4_800_000 * 1900 - 378_000 * 10_000, 4_800_000 * 10_000), "0.11125"),
    ],
)
def test_aliquota_efetiva_bate_com_conta_de_mao_e_com_a_tabela_verificada(rbt12, conta, exato):
    assert conta == Fraction(exato)
    assert aliquota_efetiva_simples_anexo1(rbt12) == pytest.approx(float(conta), abs=1e-12)


def test_primeira_faixa_e_a_nominal_e_ha_continuidade_ate_a_5a_faixa():
    assert aliquota_efetiva_simples_anexo1(100_000) == pytest.approx(0.04)
    for teto, _, _ in FAIXAS_ANEXO_I[:-2]:  # fronteiras 1->2, 2->3, 3->4, 4->5
        assert aliquota_efetiva_simples_anexo1(teto) == pytest.approx(
            aliquota_efetiva_simples_anexo1(teto + 1), abs=1e-5
        )


def test_descontinuidade_conhecida_na_fronteira_5a_para_6a_faixa():
    """Na 6ª faixa a coluna de ICMS da repartição é '-' (Planalto, consultado em 13/10/2026):
    a alíquota efetiva CAI de 11,875% para ~8,5% ao cruzar R$ 3,6 mi. Não é bug do código."""
    antes = aliquota_efetiva_simples_anexo1(3_600_000)
    depois = aliquota_efetiva_simples_anexo1("3600000.01")
    assert antes == pytest.approx(0.11875) and depois == pytest.approx(0.085, abs=1e-6)


def test_aliquota_efetiva_nunca_excede_a_nominal_da_faixa():
    for r in (50_000, 200_000, 400_000, 900_000, 2_000_000, 4_000_000):
        nominal = next(n for t, n, _ in FAIXAS_ANEXO_I if r <= t)
        assert 0 < aliquota_efetiva_simples_anexo1(r) <= float(nominal)


@pytest.mark.parametrize("ruim", [0, -1, 4_800_000.01, 10_000_000])
def test_fora_do_dominio_levanta(ruim):
    with pytest.raises(ValueError):
        aliquota_efetiva_simples_anexo1(ruim)


def test_com_simples_uniformiza_o_imposto_e_preserva_o_resto():
    novos = com_simples(1_000_000)
    assert {c.imposto for c in novos} == {0.0845}
    for velho, novo in zip(CANAIS_ILUSTRATIVOS, novos, strict=True):
        assert (velho.nome, velho.comissao, velho.frete, velho.custo_fixo) == (
            novo.nome,
            novo.comissao,
            novo.frete,
            novo.custo_fixo,
        )


def test_relatorio_padrao_nao_muda_e_o_modo_simples_muda_e_declara_o_regime():
    base, _ = construir_relatorio(50, 1.8, 0.10, 42)
    simples, _ = construir_relatorio(50, 1.8, 0.10, 42, rbt12=1_000_000)
    assert "Simples Anexo I" not in base and "Simples Anexo I" in simples
    assert base != simples
