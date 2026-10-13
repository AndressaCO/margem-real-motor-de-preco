"""Alíquota efetiva do Simples Nacional, Anexo I (comércio).

FATO: tabela da LC 123/2006, Anexo I, redação da LC 155/2016 (vigência 01/01/2018, com
remissão à LC 214/2025), consultada no Planalto em 13/10/2026 (ver VERIFICACAO.md).

    alíquota efetiva = (RBT12 x alíquota nominal - valor a deduzir) / RBT12

No Simples a alíquota efetiva é UMA para a empresa inteira naquele mês: não varia por canal.
Atenção: a alíquota efetiva NÃO é contínua ao cruzar R$ 3,6 mi (cai de 11,875% para ~8,5%),
porque na 6ª faixa a coluna de ICMS da repartição é "-" (fonte: mesma lei). Que o ICMS passe a
ser recolhido fora do DAS é interpretação a confirmar com o contador.

Limites desta função (não tratados): sublimite estadual, ST/monofásico, DIFAL, ICMS/ISS fora
do DAS na faixa final, fator R (Anexos III/V) e meses de início de atividade. Valide com o
contador.
"""

from __future__ import annotations

from fractions import Fraction

# (teto da faixa, alíquota nominal, valor a deduzir) em R$; frações exatas para não acumular erro
FAIXAS_ANEXO_I: tuple[tuple[Fraction, Fraction, Fraction], ...] = (
    (Fraction(180_000), Fraction(400, 10_000), Fraction(0)),
    (Fraction(360_000), Fraction(730, 10_000), Fraction(5_940)),
    (Fraction(720_000), Fraction(950, 10_000), Fraction(13_860)),
    (Fraction(1_800_000), Fraction(1070, 10_000), Fraction(22_500)),
    (Fraction(3_600_000), Fraction(1430, 10_000), Fraction(87_300)),
    (Fraction(4_800_000), Fraction(1900, 10_000), Fraction(378_000)),
)
TETO_SIMPLES = FAIXAS_ANEXO_I[-1][0]


def aliquota_efetiva_simples_anexo1(rbt12: float | int | str) -> float:
    """Alíquota efetiva (fração do preço) para a receita bruta dos últimos 12 meses."""
    r = Fraction(str(rbt12))
    if r <= 0:
        raise ValueError("rbt12 deve ser positivo")
    if r > TETO_SIMPLES:
        raise ValueError("rbt12 acima de R$ 4,8 milhões: fora do Simples Nacional")
    for teto, nominal, deduzir in FAIXAS_ANEXO_I:
        if r <= teto:
            return float((r * nominal - deduzir) / r)
    raise AssertionError("inalcançável: o teto foi validado acima")  # pragma: no cover
