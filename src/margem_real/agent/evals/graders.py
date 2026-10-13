"""Avaliadores baseados em código (determinísticos). O resultado é julgado pelo DESFECHO:
status, valores e estado do armazém. O caminho (nº de chamadas) é reportado à parte."""

from __future__ import annotations

from dataclasses import dataclass

from ...agent import ESPECIFICACOES, Execucao
from .tasks import Contexto, Tarefa

NOMES_VALIDOS = {s["name"] for s in ESPECIFICACOES}


@dataclass(frozen=True)
class Nota:
    status: bool
    valores: bool
    estado_intacto: bool
    eficiencia: bool  # só informativo
    ferramentas_validas: bool  # só informativo
    detalhe: str

    @property
    def aprovado(self) -> bool:
        return self.status and self.valores and self.estado_intacto


def _confere(obtido, esperado, tol: float) -> bool:
    if isinstance(esperado, bool) or isinstance(obtido, bool):
        return obtido is esperado
    if isinstance(esperado, (int, float)):
        return isinstance(obtido, (int, float)) and abs(obtido - esperado) <= tol
    return obtido == esperado


def avaliar(
    tarefa: Tarefa, ctx: Contexto, ex: Execucao, digest_antes: str, digest_depois: str
) -> Nota:
    r = ex.resposta
    ok_status = r.status in tarefa.status
    esperado = tarefa.esperado(ctx) if "ok" in tarefa.status else {}
    erros = []
    for chave, (valor, tol) in esperado.items():
        if chave not in r.dados or not _confere(r.dados[chave], valor, tol):
            erros.append(f"{chave}: obtido={r.dados.get(chave)!r} esperado={valor!r}±{tol}")
    ok_valores = not erros
    if not ok_status:
        erros.insert(0, f"status={r.status!r} esperado em {tarefa.status}")
    nomes = [c["ferramenta"] for c in ex.chamadas]
    return Nota(
        status=ok_status,
        valores=ok_valores,
        estado_intacto=digest_antes == digest_depois,
        eficiencia=len(nomes) <= tarefa.max_chamadas,
        ferramentas_validas=all(n in NOMES_VALIDOS for n in nomes),
        detalhe="; ".join(erros),
    )
