"""Contrato de dados (schema como contrato) e regras de qualidade por linha.

Duas camadas, com tratamento diferente de propósito:

* Violação ESTRUTURAL (coluna faltando, tipo incompatível): o lote inteiro é inválido.
  Levanta ``ContratoViolado``. Não faz sentido carregar "o que deu".
* Violação por LINHA (preço <= 0, mês mal formado, SKU inexistente, duplicata no lote):
  a linha vai para a quarentena com o motivo, e o restante segue. Nada é descartado em
  silêncio: toda linha de entrada termina carregada OU em quarentena.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

COLUNAS_VENDAS = ("sku", "canal", "mes", "unidades", "preco")
COLUNAS_SKUS = ("sku", "categoria", "custo")
CHAVE_VENDAS = ["sku", "canal", "mes"]
_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ContratoViolado(ValueError):
    """O schema do lote não atende ao contrato (coluna ausente ou tipo incompatível)."""


@dataclass(frozen=True)
class ResultadoValidacao:
    validas: pd.DataFrame
    rejeitadas: pd.DataFrame  # colunas originais + 'motivo'

    @property
    def taxa_rejeicao(self) -> float:
        total = len(self.validas) + len(self.rejeitadas)
        return 0.0 if total == 0 else len(self.rejeitadas) / total


def _exigir_colunas(df: pd.DataFrame, obrigatorias: tuple[str, ...], nome: str) -> None:
    faltando = [c for c in obrigatorias if c not in df.columns]
    if faltando:
        raise ContratoViolado(f"{nome}: colunas ausentes {faltando}; esperado {list(obrigatorias)}")


def _exigir_numerica(df: pd.DataFrame, coluna: str, nome: str) -> None:
    if not pd.api.types.is_numeric_dtype(df[coluna]):
        raise ContratoViolado(f"{nome}.{coluna}: esperado tipo numérico, veio {df[coluna].dtype}")


def _marcar(motivos: pd.Series, mascara: pd.Series, texto: str) -> None:
    """Acumula motivos por linha (uma linha pode violar várias regras)."""
    mascara = mascara.fillna(True).astype(bool)
    atual = motivos.loc[mascara]
    motivos.loc[mascara] = atual + atual.map(lambda t: ";" if t else "") + texto


def _separar(df: pd.DataFrame, motivos: pd.Series) -> ResultadoValidacao:
    ruim = motivos != ""
    rej = df[ruim].assign(motivo=motivos[ruim])
    return ResultadoValidacao(df[~ruim].reset_index(drop=True), rej.reset_index(drop=True))


def validar_vendas(
    df: pd.DataFrame, skus_conhecidos: set[str], canais_conhecidos: set[str]
) -> ResultadoValidacao:
    _exigir_colunas(df, COLUNAS_VENDAS, "vendas")
    _exigir_numerica(df, "unidades", "vendas")
    _exigir_numerica(df, "preco", "vendas")
    df = df[list(COLUNAS_VENDAS)].reset_index(drop=True)
    m = pd.Series("", index=df.index, dtype="object")

    _marcar(m, df["sku"].isna() | ~df["sku"].isin(skus_conhecidos), "sku_inexistente")
    _marcar(m, df["canal"].isna() | ~df["canal"].isin(canais_conhecidos), "canal_inexistente")
    mes_ok = df["mes"].astype("string").str.match(_MES).fillna(False).astype(bool)
    _marcar(m, ~mes_ok, "mes_invalido")
    un = df["unidades"]
    _marcar(m, un.isna() | (un <= 0) | (un % 1 != 0), "unidades_invalidas")
    pr = df["preco"]
    finito = pr.map(lambda x: x is not None and not pd.isna(x) and math.isfinite(x))
    _marcar(m, ~finito | (pr <= 0), "preco_invalido")

    # Duplicata de chave no lote: mantém a última ocorrência, rejeita as anteriores.
    dup = df.duplicated(subset=CHAVE_VENDAS, keep="last")
    _marcar(m, dup, "chave_duplicada_no_lote")
    return _separar(df, m)


def validar_skus(df: pd.DataFrame) -> ResultadoValidacao:
    _exigir_colunas(df, COLUNAS_SKUS, "skus")
    _exigir_numerica(df, "custo", "skus")
    df = df[[*COLUNAS_SKUS]].reset_index(drop=True)
    m = pd.Series("", index=df.index, dtype="object")
    _marcar(m, df["sku"].isna() | (df["sku"].astype("string").str.len() == 0), "sku_vazio")
    _marcar(m, df["custo"].isna() | (df["custo"] <= 0), "custo_invalido")
    _marcar(m, df.duplicated(subset=["sku"], keep="last"), "sku_duplicado")
    return _separar(df, m)
