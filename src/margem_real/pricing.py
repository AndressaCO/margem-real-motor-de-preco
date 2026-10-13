"""Funções de preço e margem.

Todas as despesas proporcionais ao preço (imposto, comissão, frete, devolução, CAC)
entram juntas em ``despesas_sobre_preco``, como fração (34% = 0.34). Custos fixos
por pedido (ex.: taxa fixa de marketplace) entram em ``custo_fixo``, em R$.

Fórmulas (derivadas de  preço - custo - fixo - preço*despesas = preço*margem):

    preço mínimo   = (custo + fixo) / (1 - despesas)
    preço sugerido = (custo + fixo) / (1 - despesas - margem)
    margem líquida = (preço - custo - fixo - preço*despesas) / preço

Preços são arredondados PARA CIMA ao centavo: arredondar para baixo faria o preço
cair abaixo do ponto de equilíbrio ou da margem pedida.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


def _d(valor: float | int | str | Decimal) -> Decimal:
    # str() evita o ruído binário de float (0.34 vira exatamente 0.34).
    return Decimal(str(valor))


def _validar(custo: Decimal, despesas: Decimal, margem: Decimal, fixo: Decimal) -> None:
    if custo < 0 or fixo < 0:
        raise ValueError("custo e custo_fixo não podem ser negativos")
    if not (Decimal(0) <= despesas < Decimal(1)):
        raise ValueError("despesas_sobre_preco deve estar em [0, 1) (use fração: 34% = 0.34)")
    if margem < 0:
        raise ValueError("margem não pode ser negativa")
    if despesas + margem >= Decimal(1):
        raise ValueError(
            "despesas_sobre_preco + margem >= 100%: nenhum preço positivo entrega essa margem"
        )


def preco_minimo(custo: float, despesas_sobre_preco: float, custo_fixo: float = 0.0) -> float:
    """Menor preço com margem de contribuição zero (ponto de equilíbrio), em R$."""
    c, d, f = _d(custo), _d(despesas_sobre_preco), _d(custo_fixo)
    _validar(c, d, Decimal(0), f)
    return float(((c + f) / (1 - d)).quantize(_CENT, rounding=ROUND_CEILING))


def preco_sugerido(
    custo: float, despesas_sobre_preco: float, margem: float, custo_fixo: float = 0.0
) -> float:
    """Preço que entrega a margem líquida alvo (fração do preço), em R$."""
    c, d, m, f = _d(custo), _d(despesas_sobre_preco), _d(margem), _d(custo_fixo)
    _validar(c, d, m, f)
    return float(((c + f) / (1 - d - m)).quantize(_CENT, rounding=ROUND_CEILING))


def margem_liquida(
    preco: float, custo: float, despesas_sobre_preco: float, custo_fixo: float = 0.0
) -> float:
    """Margem de contribuição como fração do preço (0.15 = 15%). Pode ser negativa."""
    p, c, d, f = _d(preco), _d(custo), _d(despesas_sobre_preco), _d(custo_fixo)
    _validar(c, d, Decimal(0), f)
    if p <= 0:
        raise ValueError("preco deve ser positivo")
    return float((p - c - f - p * d) / p)


def margem_com_markup(
    custo: float, markup: float, despesas_sobre_preco: float, custo_fixo: float = 0.0
) -> float:
    """Margem líquida de quem precifica por markup fixo sobre o custo."""
    return margem_liquida(float(_d(custo) * _d(markup)), custo, despesas_sobre_preco, custo_fixo)


def markup_para_margem(
    custo: float, despesas_sobre_preco: float, margem: float, custo_fixo: float = 0.0
) -> float:
    """Markup que o canal exigiria para entregar a margem alvo (varia por canal e por SKU)."""
    preco = preco_sugerido(custo, despesas_sobre_preco, margem, custo_fixo)
    return float((_d(preco) / _d(custo)).quantize(_CENT, rounding=ROUND_HALF_UP))


def brl(valor: float) -> str:
    """Formata em reais no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    q = _d(valor).quantize(_CENT, rounding=ROUND_HALF_UP)
    inteiro, _, centavos = f"{abs(q):,.2f}".partition(".")
    sinal = "-" if q < 0 else ""
    return f"{sinal}R$ {inteiro.replace(',', '.')},{centavos}"
