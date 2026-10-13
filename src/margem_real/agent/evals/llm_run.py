"""Avaliação com LLM real: ``python -m margem_real.agent.evals --llm-modelo <id>``.

Grava em ``evals/llm/<modelo>/`` (não toca em ``evals/resultados.json``, que é o resultado
determinístico e reproduzível sem chave). Exige ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..llm import Cliente, PlanejadorClaude, Uso, cliente_http
from ..llm_chat import PlanejadorChat, cliente_gemini
from .metrics import agregar
from .runner import gravar_transcricoes, rodar
from .tasks import TAREFAS, contexto

PROVEDORES = ("anthropic", "gemini")
SPLITS = {"dev": ("dev",), "heldout": ("heldout",), "todos": ("dev", "heldout")}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _slug(modelo: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", modelo)


def rodar_llm(
    modelo: str,
    trials: int,
    split: str,
    saida: Path,
    cliente: Cliente | None = None,
    temperatura: float | None = None,
    provedor: str = "anthropic",
) -> dict[str, Any]:
    ctx = contexto()
    if provedor not in PROVEDORES:
        raise ValueError(f"provedor desconhecido: {provedor}")
    fabrica_cliente = cliente_gemini if provedor == "gemini" else cliente_http
    classe = PlanejadorChat if provedor == "gemini" else PlanejadorClaude
    cli = cliente or fabrica_cliente()
    # a documentação do Gemini só mostra tool_choice "auto"; o prompt manda chamar `responder`
    extra: dict[str, Any] = {"tool_choice": "auto"} if provedor == "gemini" else {}
    uso = Uso()
    tarefas = tuple(t for t in TAREFAS if t.split in SPLITS[split])
    res = rodar(
        lambda i: classe(modelo, cli, temperatura=temperatura, uso=uso, **extra),
        ctx,
        trials,
        tarefas,
    )
    split_de = {t.id: t.split for t in TAREFAS}
    resumo: dict[str, Any] = {
        "modelo": modelo,
        "provedor": provedor,
        "trials": trials,
        "tarefas": len(tarefas),
        "uso": {
            "chamadas_api": uso.chamadas,
            "tokens_entrada": uso.tokens_entrada,
            "tokens_saida": uso.tokens_saida,
            "segundos_api": round(uso.segundos, 1),
        },
        "conjuntos": {},
    }
    for sp in SPLITS[split]:
        sub = [r for r in res if split_de[r.tarefa] == sp]
        por: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for r in sub:
            por[r.tarefa][0] += 1
            por[r.tarefa][1] += int(r.nota.aprovado)
        resumo["conjuntos"][sp] = {
            "tarefas": len(por),
            "metricas": agregar(
                {k: (v[0], v[1]) for k, v in por.items()}, tuple(range(1, trials + 1))
            ),
            "falhas": [
                {"tarefa": r.tarefa, "trial": r.trial, "detalhe": r.nota.detalhe}
                for r in sub
                if not r.nota.aprovado
            ][:80],
            "estado_alterado": sum(1 for r in sub if not r.nota.estado_intacto),
            "ferramenta_invalida": sum(1 for r in sub if not r.nota.ferramentas_validas),
        }
    destino = saida / "llm" / _slug(modelo)
    destino.mkdir(parents=True, exist_ok=True)
    gravar_transcricoes(res, destino / "transcripts.jsonl", f"llm:{modelo}")
    (destino / "resultados.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destino / "RELATORIO.md").write_text(renderizar(resumo), encoding="utf-8")
    return resumo


def renderizar(r: dict[str, Any]) -> str:
    ks = sorted(next(iter(r["conjuntos"].values()))["metricas"]["pass@k"], key=int)
    cab = ["Conjunto", "Tarefas"] + [f"pass@{k}" for k in ks] + [f"pass^{k}" for k in ks]
    linhas = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for sp, v in r["conjuntos"].items():
        m = v["metricas"]
        cel = [sp, str(v["tarefas"])]
        cel += [_pct(m["pass@k"][k]) for k in ks] + [_pct(m["pass^k"][k]) for k in ks]
        linhas.append("| " + " | ".join(cel) + " |")
    falhas = []
    for sp, v in r["conjuntos"].items():
        vistos: dict[str, str] = {}
        for f in v["falhas"]:
            vistos.setdefault(f["tarefa"], f["detalhe"])
        falhas += [f"- ({sp}) `{t}`: {d}" for t, d in vistos.items()]
    u = r["uso"]
    controles = "\n".join(
        f"- {sp}: estado alterado = {v['estado_alterado']}, ferramenta inválida = "
        f"{v['ferramenta_invalida']}"
        for sp, v in r["conjuntos"].items()
    )
    return (
        f"# Avaliação do agente com LLM: `{r['modelo']}` via {r.get('provedor', 'anthropic')} "
        "(gerado; não edite à mão)\n\n"
        f"Tarefas: {r['tarefas']} · trials por tarefa: {r['trials']} · "
        "ambiente isolado por trial.\n\n"
        "## Métricas\n\n" + "\n".join(linhas) + "\n\n"
        "- Mesmas tarefas, ferramentas e avaliadores por estado final do planejador de regras; "
        "só o planejador muda.\n"
        "- Execução única, sem repetição entre dias: o resultado de um modelo varia com versão, "
        "temperatura e carga da API. Trate como medida pontual, não como propriedade do modelo.\n\n"
        "## Uso\n\n"
        f"- Chamadas à API: {u['chamadas_api']} · tokens de entrada: {u['tokens_entrada']} · "
        f"tokens de saída: {u['tokens_saida']} · tempo em API: {u['segundos_api']} s\n\n"
        "## Falhas (1ª ocorrência por tarefa)\n\n"
        + ("\n".join(falhas) if falhas else "_Nenhuma falha._")
        + "\n\n## Controles de processo (devem ser zero)\n\n"
        + controles
        + "\n"
    )
