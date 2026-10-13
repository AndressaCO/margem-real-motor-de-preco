"""Métricas de avaliação com n tentativas (trials) por tarefa.

* pass@k (Chen et al., 2021, arXiv:2107.03374): probabilidade de PELO MENOS UM de k trials
  sorteados (sem reposição) entre n passar:  1 - C(n-c, k) / C(n, k).
* pass^k (Yao et al., 2024, arXiv:2406.12045, tau-bench): probabilidade de TODOS os k trials
  passarem:  C(c, k) / C(n, k). Mede consistência, o que importa quando o agente age sozinho.
"""

from __future__ import annotations

from fractions import Fraction
from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    if not (0 <= c <= n) or not (1 <= k <= n):
        raise ValueError("exige 0 <= c <= n e 1 <= k <= n")
    if n - c < k:
        return 1.0
    return float(1 - Fraction(comb(n - c, k), comb(n, k)))  # exato: evita 0,19999… em vez de 0,2


def pass_pow_k(n: int, c: int, k: int) -> float:
    if not (0 <= c <= n) or not (1 <= k <= n):
        raise ValueError("exige 0 <= c <= n e 1 <= k <= n")
    return float(Fraction(comb(c, k), comb(n, k)))


def agregar(
    contagens: dict[str, tuple[int, int]], ks: tuple[int, ...]
) -> dict[str, dict[int, float]]:
    """contagens[tarefa] = (n, c). Devolve a média das métricas sobre as tarefas."""
    out: dict[str, dict[int, float]] = {"pass@k": {}, "pass^k": {}}
    for k in ks:
        validas = [(n, c) for n, c in contagens.values() if n >= k]
        if not validas:
            continue
        out["pass@k"][k] = sum(pass_at_k(n, c, k) for n, c in validas) / len(validas)
        out["pass^k"][k] = sum(pass_pow_k(n, c, k) for n, c in validas) / len(validas)
    return out
