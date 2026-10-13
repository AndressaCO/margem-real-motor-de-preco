"""Preenche no README a tabela de avaliação a partir de evals/resultados.json.

Nenhum número da tabela é digitado à mão: rode `make evals` e depois este script.
Uso: python scripts/atualizar_readme.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INI, FIM = "<!-- eval:begin -->", "<!-- eval:end -->"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def bloco(res: dict) -> str:
    primeiro = next(iter(res["planejadores"].values()))["dev"]["metricas"]["pass^k"]
    kmax = max(primeiro, key=int)  # maior k disponível (= nº de trials)
    linhas = [
        f"| Planejador | Conjunto | Tarefas | pass@1 | pass^1 | pass^{kmax} |",
        "|---|---|---|---|---|---|",
    ]
    for nome, d in res["planejadores"].items():
        for sp, v in d.items():
            m = v["metricas"]
            linhas.append(
                f"| {nome} | {sp} | {v['tarefas']} | {_pct(m['pass@k']['1'])} | "
                f"{_pct(m['pass^k']['1'])} | {_pct(m['pass^k'][kmax])} |"
            )
    return "\n".join(linhas)


def aplicar(readme: str, res: dict) -> str:
    novo = f"{INI}\n{bloco(res)}\n{FIM}"
    padrao = re.compile(re.escape(INI) + r".*?" + re.escape(FIM), re.S)
    if not padrao.search(readme):
        raise SystemExit("marcadores <!-- eval:begin/end --> ausentes no README")
    return padrao.sub(lambda _: novo, readme)


def main() -> None:
    res = json.loads((RAIZ / "evals" / "resultados.json").read_text(encoding="utf-8"))
    p = RAIZ / "README.md"
    atual = p.read_text(encoding="utf-8")
    novo = aplicar(atual, res)
    if "--check" in sys.argv:
        sys.exit(0 if novo == atual else 1)
    p.write_text(novo, encoding="utf-8")


if __name__ == "__main__":
    main()
