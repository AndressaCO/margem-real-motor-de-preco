"""Margem Real: preço mínimo e sugerido por SKU e canal."""

from .pricing import (
    brl,
    margem_com_markup,
    margem_liquida,
    markup_para_margem,
    preco_minimo,
    preco_sugerido,
)

__all__ = [
    "brl",
    "margem_com_markup",
    "margem_liquida",
    "markup_para_margem",
    "preco_minimo",
    "preco_sugerido",
]
__version__ = "0.1.0"
