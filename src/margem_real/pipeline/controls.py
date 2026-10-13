"""Controles de dados no estilo controladoria: conciliação e frescor (SLA)."""

from __future__ import annotations

from datetime import UTC, datetime

from ..analysis import margem_por_sku_canal
from .store import Armazem


def conciliar(armazem: Armazem) -> dict:
    """Concilia a camada bruta (vendas) com a camada de consumo (margem por SKU x canal).

    Controle de totais: receita e unidades têm que fechar. A tolerância reconhece que a
    camada de consumo arredonda a receita por par a 2 casas: até R$ 0,005 por par.
    """
    v, s, c = armazem.tabelas_para_analise()
    mart = margem_por_sku_canal(v, s, c)
    receita_bruta = float((v["unidades"] * v["preco"]).sum())
    receita_mart = float(mart["receita"].sum())
    pares = len(mart)
    tolerancia = 0.005 * pares
    dif_receita = abs(receita_bruta - receita_mart)
    dif_unid = int(v["unidades"].sum() - mart["unidades"].sum())
    return {
        "receita_bruta": round(receita_bruta, 2),
        "receita_consumo": round(receita_mart, 2),
        "diferenca_receita": round(dif_receita, 4),
        "tolerancia": round(tolerancia, 4),
        "diferenca_unidades": dif_unid,
        "pares": pares,
        "aprovado": dif_receita <= tolerancia and dif_unid == 0,
    }


def frescor(armazem: Armazem, sla_horas: float, agora: datetime | None = None) -> dict:
    """Idade da última carga de vendas aceita contra o SLA de frescor."""
    r = armazem.escalar(
        "SELECT max(executado_em) FROM execucoes WHERE tabela = 'vendas' AND status = 'ok'"
    )
    if r is None:
        return {
            "ultima_carga": None,
            "idade_horas": None,
            "sla_horas": sla_horas,
            "aprovado": False,
        }
    agora = (agora or datetime.now(UTC)).replace(tzinfo=None)
    idade = (agora - r).total_seconds() / 3600
    return {
        "ultima_carga": r.isoformat(),
        "idade_horas": round(idade, 2),
        "sla_horas": sla_horas,
        "aprovado": idade <= sla_horas,
    }
