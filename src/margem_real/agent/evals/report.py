"""Gera evals/RELATORIO.md a partir de resultados.json (nenhum número é digitado à mão)."""

from __future__ import annotations


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%".replace(".", ",")


def _ks(res: dict) -> list[str]:
    """Os k disponíveis (dependem do número de trials rodados)."""
    primeiro = next(iter(res["planejadores"].values()))["dev"]["metricas"]["pass@k"]
    return sorted(primeiro, key=int)


def _tabela_metricas(res: dict) -> str:
    ks = _ks(res)
    cab = (
        ["Planejador", "Conjunto", "Tarefas"]
        + [f"pass@{k}" for k in ks]
        + [f"pass^{k}" for k in ks]
    )
    linhas = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for nome, d in res["planejadores"].items():
        for sp, v in d.items():
            m = v["metricas"]
            cel = [nome, sp, str(v["tarefas"])]
            cel += [_pct(m["pass@k"][k]) for k in ks] + [_pct(m["pass^k"][k]) for k in ks]
            linhas.append("| " + " | ".join(cel) + " |")
    return "\n".join(linhas)


def _tabela_categorias(res: dict) -> str:
    linhas = [
        "| Planejador | Conjunto | Categoria | Taxa de aprovação (por trial) |",
        "|---|---|---|---|",
    ]
    for nome, d in res["planejadores"].items():
        for sp, v in d.items():
            for cat, taxa in sorted(v["por_categoria"].items()):
                linhas.append(f"| {nome} | {sp} | {cat} | {_pct(taxa)} |")
    return "\n".join(linhas)


def _falhas_heldout(res: dict) -> str:
    v = res["planejadores"]["regras"]["heldout"]
    vistos: dict[str, str] = {}
    for f in v["falhas"]:
        vistos.setdefault(f["tarefa"], f["detalhe"])
    if not vistos:
        return "_Nenhuma falha no conjunto held-out._"
    return "\n".join(
        f"- `{t}`: {d}" for t, d in sorted(vistos.items(), key=lambda x: int(x[0][1:]))
    )


def renderizar(res: dict) -> str:
    return (
        f"""# Relatório de avaliação do agente (gerado por `python -m margem_real.agent.evals`)

Tarefas: {res["tarefas"]} · trials por tarefa: {res["trials"]} · ambiente isolado por trial.
Não edite à mão: este arquivo é sobrescrito a cada execução.

## Métricas

{_tabela_metricas(res)}

- **dev**: tarefas usadas enquanto o planejador de regras era escrito. **heldout**: escritas
  depois, sem ajustar o planejador a elas (mede generalização).
- `regras` é um stand-in determinístico de um LLM (regex sobre texto), não um modelo.
  `ruidoso` injeta falhas sintéticas com taxa conhecida para provar que o harness detecta falha.
  Nenhum número aqui mede um modelo de linguagem.
- pass@k: chance de pelo menos 1 de k trials passar; pass^k: chance de todos os k passarem.

## Por categoria

{_tabela_categorias(res)}

## Falhas do planejador de regras no conjunto held-out (1ª ocorrência por tarefa)

{_falhas_heldout(res)}

## Controles de processo (devem ser zero)

"""
        + "\n".join(
            f"- {n} / {sp}: estado alterado = {v['estado_alterado']}, ferramenta inválida = "
            f"{v['ferramenta_invalida']}"
            for n, d in res["planejadores"].items()
            for sp, v in d.items()
            if n == "regras"
        )
        + "\n"
    )
