"""CLI: gera dados sintéticos, calcula margens e escreve o relatório em Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .analysis import abaixo_do_minimo, margem_por_sku_canal, repricing, resumo_por_canal
from .channels import canais_dataframe
from .pricing import brl
from .synthetic import gerar_skus, gerar_vendas

AVISO = (
    "> Dados 100% sintéticos e parâmetros de canal ilustrativos. "
    "Valide alíquotas e regime com seu contador."
)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _tabela_md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def construir_relatorio(
    n_skus: int, markup: float, margem_alvo: float, semente: int
) -> tuple[str, pd.DataFrame]:
    skus = gerar_skus(n_skus, semente)
    canais = canais_dataframe()
    vendas = gerar_vendas(skus, markup=markup, semente=semente)
    margem = margem_por_sku_canal(vendas, skus, canais)
    resumo = resumo_por_canal(margem)
    prejuizo = abaixo_do_minimo(margem)
    novo = repricing(margem, canais, margem_alvo)

    receita_total = margem["receita"].sum()
    mc_total = margem["margem_contribuicao"].sum()
    rec_prej = prejuizo["receita"].sum()

    tabela_canal = resumo.assign(
        receita=resumo["receita"].map(brl),
        margem_contribuicao=resumo["margem_contribuicao"].map(brl),
        margem_pct=resumo["margem_pct"].map(_pct),
        pct_pares_no_prejuizo=resumo["pct_pares_no_prejuizo"].map(_pct),
    )[["canal", "pares", "receita", "margem_contribuicao", "margem_pct", "pct_pares_no_prejuizo"]]

    piores = (
        novo.sort_values("margem_contribuicao")
        .head(8)[
            [
                "sku",
                "canal",
                "preco_medio_praticado",
                "preco_minimo",
                "preco_sugerido",
                "variacao_pct",
            ]
        ]
        .assign(
            preco_medio_praticado=lambda d: d["preco_medio_praticado"].map(brl),
            preco_minimo=lambda d: d["preco_minimo"].map(brl),
            preco_sugerido=lambda d: d["preco_sugerido"].map(brl),
            variacao_pct=lambda d: d["variacao_pct"].map(_pct),
        )
    )

    texto = f"""# Relatório de margem por SKU e canal

{AVISO}

Parâmetros: {n_skus} SKUs, markup fixo de {str(markup).replace(".", ",")} em todos os canais,
margem alvo de {_pct(margem_alvo)}, semente {semente}.

## Visão geral

- Receita total simulada: {brl(receita_total)}
- Margem de contribuição total: {brl(mc_total)} ({_pct(mc_total / receita_total)})
- Pares SKU x canal vendendo abaixo do preço mínimo: {len(prejuizo)} de {len(margem)}
  ({_pct(len(prejuizo) / len(margem))}), somando {_pct(rec_prej / receita_total)} da receita

## Por canal

{_tabela_md(tabela_canal)}

## Oito piores pares e o preço que a conta exige

{_tabela_md(piores)}

## Hipóteses e limites

- O preço sugerido não modela elasticidade: subir preço pode reduzir volume.
- Os custos de canal são ilustrativos e iguais para todos os SKUs de um canal.
- Custos fixos da operação (folha, aluguel) ficam fora da margem de contribuição.
"""
    return texto, margem


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="margem-real", description=__doc__)
    p.add_argument("--skus", type=int, default=200)
    p.add_argument("--markup", type=float, default=1.80)
    p.add_argument("--margem-alvo", type=float, default=0.10)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--saida", type=Path, default=Path("reports/relatorio.md"))
    p.add_argument("--csv", type=Path, default=Path("reports/margem_por_sku_canal.csv"))
    args = p.parse_args(argv)

    texto, margem = construir_relatorio(args.skus, args.markup, args.margem_alvo, args.semente)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(texto, encoding="utf-8")
    margem.to_csv(args.csv, index=False)
    print(texto)
    print(f"\nEscrito em {args.saida} e {args.csv}")


if __name__ == "__main__":
    main()
