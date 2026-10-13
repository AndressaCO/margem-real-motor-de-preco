"""Análise de margem por SKU x canal (SQL em DuckDB) e simulação de repricing."""

from __future__ import annotations

from importlib import resources

import duckdb
import pandas as pd

from .pricing import preco_sugerido


def _sql(nome: str) -> str:
    return (resources.files("margem_real") / "sql" / nome).read_text(encoding="utf-8")


def margem_por_sku_canal(
    vendas: pd.DataFrame, skus: pd.DataFrame, canais: pd.DataFrame
) -> pd.DataFrame:
    """Margem de contribuição, preço mínimo e preço praticado por SKU x canal."""
    con = duckdb.connect(":memory:")
    try:
        con.register("vendas", vendas)
        con.register("skus", skus)
        con.register("canais", canais)
        return con.execute(_sql("margem_contribuicao.sql")).df()
    finally:
        con.close()


def resumo_por_canal(margem: pd.DataFrame) -> pd.DataFrame:
    """Receita, margem e participação de pares SKU x canal no prejuízo, por canal."""
    g = margem.assign(prejuizo=margem["margem_contribuicao"] < 0).groupby("canal")
    out = g.agg(
        pares=("sku", "count"),
        receita=("receita", "sum"),
        margem_contribuicao=("margem_contribuicao", "sum"),
        pares_no_prejuizo=("prejuizo", "sum"),
    )
    out["margem_pct"] = out["margem_contribuicao"] / out["receita"]
    out["pct_pares_no_prejuizo"] = out["pares_no_prejuizo"] / out["pares"]
    return out.reset_index().sort_values(["margem_pct", "canal"])


def abaixo_do_minimo(margem: pd.DataFrame) -> pd.DataFrame:
    """Pares cujo preço médio praticado está abaixo do preço mínimo (vendem no prejuízo)."""
    return margem[margem["preco_medio_praticado"] < margem["preco_minimo"]]


def repricing(margem: pd.DataFrame, canais: pd.DataFrame, margem_alvo: float) -> pd.DataFrame:
    """Preço sugerido por par para a margem alvo, e a variação sobre o preço praticado.

    Hipótese explícita: não modela elasticidade. Subir preço pode derrubar volume;
    o resultado mostra o preço que a conta exige, não a receita futura.
    """
    base = margem.merge(canais[["canal", "pct_despesas", "custo_fixo"]], on="canal")
    base["preco_sugerido"] = [
        preco_sugerido(
            float(r["custo"]), float(r["pct_despesas"]), margem_alvo, float(r["custo_fixo"])
        )
        for r in base.to_dict("records")
    ]
    base["variacao_pct"] = base["preco_sugerido"] / base["preco_medio_praticado"] - 1
    return base.drop(columns=["pct_despesas", "custo_fixo"])
