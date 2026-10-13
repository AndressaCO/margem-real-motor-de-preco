"""Parâmetros de canal.

ATENÇÃO: todos os valores abaixo são ILUSTRATIVOS. Não representam a tabela de nenhum
marketplace real nem a carga tributária de nenhuma empresa. Troque pelos seus números.
Valide alíquotas e regime com seu contador.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Canal:
    nome: str
    imposto: float  # fração do preço
    comissao: float  # fração do preço (comissão de marketplace ou gateway)
    frete: float  # fração do preço (frete subsidiado pelo vendedor)
    devolucao: float  # fração do preço (devoluções e cancelamentos)
    cac: float  # fração do preço (mídia paga e promoções)
    custo_fixo: float = 0.0  # R$ por unidade vendida (taxa fixa)

    @property
    def despesas_sobre_preco(self) -> float:
        return round(self.imposto + self.comissao + self.frete + self.devolucao + self.cac, 6)


CANAIS_ILUSTRATIVOS: tuple[Canal, ...] = (
    Canal("marketplace_a", 0.08, 0.16, 0.05, 0.03, 0.04, custo_fixo=6.00),
    Canal("marketplace_b", 0.08, 0.12, 0.07, 0.04, 0.06),
    Canal("site_proprio", 0.08, 0.035, 0.06, 0.02, 0.10),
    Canal("b2b_distribuicao", 0.10, 0.00, 0.02, 0.01, 0.02),
)


def canais_dataframe(canais: tuple[Canal, ...] = CANAIS_ILUSTRATIVOS) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "canal": c.nome,
                "pct_despesas": c.despesas_sobre_preco,
                "custo_fixo": c.custo_fixo,
                "imposto": c.imposto,
                "comissao": c.comissao,
                "frete": c.frete,
                "devolucao": c.devolucao,
                "cac": c.cac,
            }
            for c in canais
        ]
    )
