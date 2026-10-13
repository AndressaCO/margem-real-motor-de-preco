"""Camada de engenharia de dados: contrato, ingestão idempotente, quarentena e controles."""

from .contracts import ContratoViolado, ResultadoValidacao, validar_skus, validar_vendas
from .controls import conciliar, frescor
from .store import Armazem, QualidadeError, ResumoCarga

__all__ = [
    "Armazem",
    "ContratoViolado",
    "QualidadeError",
    "ResultadoValidacao",
    "ResumoCarga",
    "conciliar",
    "frescor",
    "validar_skus",
    "validar_vendas",
]
