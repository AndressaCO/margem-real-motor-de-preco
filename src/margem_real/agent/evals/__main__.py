"""python -m margem_real.agent.evals  ->  roda as avaliações e grava relatório + transcrições."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from .. import PlanejadorRegras, PlanejadorRuidoso
from ..agent import Planejador
from .metrics import agregar
from .report import renderizar
from .runner import gravar_transcricoes, rodar
from .tasks import TAREFAS, contexto

KS = (1, 3, 5)


def _contagens(res):
    por: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in res:
        por[r.tarefa][0] += 1
        por[r.tarefa][1] += int(r.nota.aprovado)
    return {k: (v[0], v[1]) for k, v in por.items()}


def _por_categoria(res):
    por: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in res:
        por[r.categoria][0] += 1
        por[r.categoria][1] += int(r.nota.aprovado)
    return {k: v[1] / v[0] for k, v in por.items()}


def _resumo(res):
    return {
        "tarefas": len({r.tarefa for r in res}),
        "metricas": agregar(_contagens(res), KS),
        "por_categoria": _por_categoria(res),
        "falhas": [
            {"tarefa": r.tarefa, "trial": r.trial, "detalhe": r.nota.detalhe}
            for r in res
            if not r.nota.aprovado
        ][:60],
        "fora_de_eficiencia": sum(1 for r in res if not r.nota.eficiencia),
        "ferramenta_invalida": sum(1 for r in res if not r.nota.ferramentas_validas),
        "estado_alterado": sum(1 for r in res if not r.nota.estado_intacto),
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="margem-real-evals", description=__doc__)
    p.add_argument("--trials", type=int, default=5)
    p.add_argument("--p-erro", type=float, default=0.25)
    p.add_argument("--saida", type=Path, default=Path("evals"))
    a = p.parse_args(argv)
    ctx = contexto()
    cenarios: dict[str, Callable[[int], Planejador]] = {
        "regras": lambda i: PlanejadorRegras(),
        f"ruidoso(p={a.p_erro})": lambda i: PlanejadorRuidoso(PlanejadorRegras(), a.p_erro, 11, i),
    }
    resumo: dict = {"tarefas": len(TAREFAS), "trials": a.trials, "planejadores": {}}
    for nome, fab in cenarios.items():
        res = rodar(fab, ctx, a.trials)
        gravar_transcricoes(res, a.saida / "transcripts" / f"{nome.split('(')[0]}.jsonl", nome)
        split_de = {t.id: t.split for t in TAREFAS}
        resumo["planejadores"][nome] = {
            sp: _resumo([r for r in res if split_de[r.tarefa] == sp]) for sp in ("dev", "heldout")
        }
    a.saida.mkdir(parents=True, exist_ok=True)
    (a.saida / "resultados.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    relido = json.loads(json.dumps(resumo))  # chaves viram str, como no arquivo gravado
    (a.saida / "RELATORIO.md").write_text(renderizar(relido), encoding="utf-8")
    print(
        json.dumps(
            {
                n: {sp: v["metricas"] for sp, v in d.items()}
                for n, d in resumo["planejadores"].items()
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
