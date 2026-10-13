"""Emite como anotações do GitHub Actions uma amostra das transcrições do LLM (leitura sem baixar).

Uso: python scripts/anotar_transcricoes.py evals/llm/<modelo>/transcripts.jsonl [máx=10]
Escolhe as reprovadas primeiro e completa com aprovadas de tarefas diferentes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _texto(linha: dict) -> str:
    passos = []
    for p in linha["transcricao"]:
        if p["tipo"] == "pergunta":
            passos.append(f"P: {p['texto']}")
        elif p["tipo"] == "chamada":
            passos.append(f"-> {p['ferramenta']}({json.dumps(p['args'], ensure_ascii=False)})")
        elif p["tipo"] == "resultado":
            passos.append(f"<- {json.dumps(p['resultado'], ensure_ascii=False)[:300]}")
        else:
            passos.append(f"R[{p.get('status')}]: {str(p.get('texto'))[:200]} {p.get('dados')}")
    cab = (
        f"{linha['tarefa']} trial {linha['trial']} aprovado={linha['aprovado']} {linha['detalhe']}"
    )
    return (cab + "\n" + "\n".join(passos))[:2800]


def main(caminho: str, maximo: int = 10) -> None:
    linhas = [json.loads(x) for x in Path(caminho).read_text(encoding="utf-8").splitlines() if x]
    ruins = [x for x in linhas if not x["aprovado"]]
    vistos: set[str] = set()
    boas = []
    for x in linhas:
        if x["aprovado"] and x["tarefa"] not in vistos:
            vistos.add(x["tarefa"])
            boas.append(x)
    for x in (ruins + boas)[:maximo]:
        msg = _texto(x).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::notice title=transcrição {x['tarefa']}::{msg}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)
