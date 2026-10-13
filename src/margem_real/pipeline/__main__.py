"""Demonstra a carga: 1ª carga, reenvio idêntico (idempotência) e lote corrompido (bloqueio)."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ..channels import canais_dataframe
from ..synthetic import gerar_skus, gerar_vendas
from . import Armazem, QualidadeError, conciliar
from .logs import configurar


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="margem-real-pipeline", description=__doc__)
    p.add_argument("--db", default=":memory:")
    p.add_argument("--skus", type=int, default=200)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--json", type=Path, default=None, help="grava o resumo da demonstração")
    a = p.parse_args(argv)
    configurar()

    skus = gerar_skus(a.skus, a.semente)
    vendas = gerar_vendas(skus, semente=a.semente)
    arm = Armazem(a.db)
    arm.carregar_canais(canais_dataframe())
    out: dict = {"skus": asdict(arm.carregar_skus(skus[["sku", "categoria", "custo"]]))}
    out["carga_1"] = asdict(arm.carregar_vendas(vendas))
    out["carga_2_mesmo_lote"] = asdict(arm.carregar_vendas(vendas))
    ruim = vendas.copy()
    ruim.loc[ruim.index[: len(ruim) // 4], "preco"] = -1.0
    try:
        arm.carregar_vendas(ruim)
        out["carga_3_corrompida"] = "ACEITA (inesperado)"
    except QualidadeError as e:
        out["carga_3_corrompida"] = f"bloqueada: {e}"
    out["conciliacao"] = conciliar(arm)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), "utf-8")


if __name__ == "__main__":
    main()
