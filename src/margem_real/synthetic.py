"""Gerador de dados sintéticos (reprodutível por semente).

Nada aqui vem de dados reais de qualquer empresa. O catálogo imita a estrutura de um
distribuidor de autopeças (categorias genéricas, custo assimétrico, poucos SKUs com
muito giro) apenas para dar forma realista ao problema.

Política de preço simulada: markup fixo único sobre o custo, em todos os canais.
É exatamente a prática que o projeto questiona.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .channels import CANAIS_ILUSTRATIVOS, Canal

CATEGORIAS = ("filtros", "freios", "suspensao", "eletrica", "lubrificantes", "arrefecimento")
MESES = pd.period_range("2026-01", periods=6, freq="M").astype(str).tolist()


def gerar_skus(n: int = 200, semente: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    custo = np.round(rng.lognormal(mean=3.6, sigma=0.9, size=n), 2).clip(4.0, 900.0)
    # Giro concentrado: poucos SKUs vendem muito (distribuição de Pareto).
    popularidade = rng.pareto(a=1.2, size=n) + 1.0
    return pd.DataFrame(
        {
            "sku": [f"SKU-{i:04d}" for i in range(1, n + 1)],
            "categoria": rng.choice(CATEGORIAS, size=n),
            "custo": custo,
            "popularidade": popularidade / popularidade.mean(),
        }
    )


def gerar_vendas(
    skus: pd.DataFrame,
    canais: tuple[Canal, ...] = CANAIS_ILUSTRATIVOS,
    markup: float = 1.80,
    semente: int = 42,
) -> pd.DataFrame:
    """Vendas mensais por SKU x canal, com preço = custo x markup (e promoções ocasionais)."""
    rng = np.random.default_rng(semente + 1)
    peso_canal = {c.nome: p for c, p in zip(canais, (1.0, 0.8, 0.5, 0.6), strict=True)}
    linhas = []
    for sku in skus.itertuples(index=False):
        for canal in canais:
            if rng.random() > 0.85:  # nem todo SKU está listado em todo canal
                continue
            for mes in MESES:
                lam = 6.0 * sku.popularidade * peso_canal[canal.nome]
                unidades = int(rng.poisson(lam))
                if unidades == 0:
                    continue
                promo = rng.random() < 0.20
                desconto = rng.uniform(0.03, 0.10) if promo else 0.0
                preco = round(sku.custo * markup * (1 - desconto), 2)
                linhas.append((sku.sku, canal.nome, mes, unidades, preco))
    return pd.DataFrame(linhas, columns=["sku", "canal", "mes", "unidades", "preco"])
