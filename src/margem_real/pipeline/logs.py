"""Log estruturado (uma linha JSON por evento) para auditoria e observabilidade."""

from __future__ import annotations

import json
import logging
import sys

LOGGER = logging.getLogger("margem_real")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {"nivel": record.levelname, "evento": record.getMessage()}
        base.update(getattr(record, "campos", {}))
        return json.dumps(base, ensure_ascii=False, sort_keys=True, default=str)


def configurar(nivel: int = logging.INFO, stream=None) -> None:
    """Idempotente: substitui o handler anterior (nunca duplica); a última chamada vale."""
    for h in list(LOGGER.handlers):
        if getattr(h, "_margem_real", False):
            LOGGER.removeHandler(h)
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(_JsonFormatter())
    handler._margem_real = True  # type: ignore[attr-defined]
    LOGGER.addHandler(handler)
    LOGGER.setLevel(nivel)
    LOGGER.propagate = False


def evento(nome: str, nivel: int = logging.INFO, **campos: object) -> None:
    LOGGER.log(nivel, nome, extra={"campos": campos})
