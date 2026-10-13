"""Execução multi-trial com ambiente isolado por trial e transcrições gravadas."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ...pipeline import Armazem
from .. import Ferramentas, executar
from ..agent import Planejador
from .graders import Nota, avaliar
from .tasks import TAREFAS, Contexto, Tarefa


@dataclass(frozen=True)
class ResultadoTrial:
    tarefa: str
    categoria: str
    trial: int
    nota: Nota
    transcricao: list[dict]


def novo_ambiente(ctx: Contexto) -> Armazem:
    """Armazém NOVO por trial: nenhum estado vaza entre tentativas."""
    a = Armazem()
    a.carregar_canais(ctx.canais)
    a.carregar_skus(ctx.skus[["sku", "categoria", "custo"]])
    a.carregar_vendas(ctx.vendas)
    return a


def rodar(
    fabrica: Callable[[int], Planejador],
    ctx: Contexto,
    trials: int = 5,
    tarefas: tuple[Tarefa, ...] = TAREFAS,
) -> list[ResultadoTrial]:
    out = []
    for t in tarefas:
        for i in range(trials):
            arm = novo_ambiente(ctx)
            antes = arm.impressao_digital()
            ex = executar(t.pergunta, fabrica(i), Ferramentas(arm))
            nota = avaliar(t, ctx, ex, antes, arm.impressao_digital())
            arm.fechar()
            out.append(ResultadoTrial(t.id, t.categoria, i, nota, ex.transcricao))
    return out


def gravar_transcricoes(resultados: list[ResultadoTrial], caminho: Path, planejador: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        for r in resultados:
            linha = {
                "planejador": planejador,
                "tarefa": r.tarefa,
                "trial": r.trial,
                "aprovado": r.nota.aprovado,
                "detalhe": r.nota.detalhe,
                "transcricao": r.transcricao,
            }
            f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")
