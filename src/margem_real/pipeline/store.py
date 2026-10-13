"""Armazém DuckDB com carga incremental idempotente, quarentena e trilha de execução.

Garantias (cada uma tem teste):

* Idempotência: reenviar o mesmo lote não altera nada (o lote é identificado pelo hash
  do conteúdo canônico). Reenviar linhas com a mesma chave (sku, canal, mes) faz upsert.
* Atomicidade: se a qualidade do lote reprova, NENHUM dado entra (rollback); a
  quarentena e a trilha de execução registram o que aconteceu.
* Rastreabilidade: cada linha carregada guarda o ``lote_id`` que a trouxe.
* Nada some em silêncio: entrada = carregadas + quarentena (invariante verificado).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .contracts import CHAVE_VENDAS, validar_skus, validar_vendas
from .logs import evento

_DDL = """
CREATE TABLE IF NOT EXISTS canais (
    canal VARCHAR PRIMARY KEY, pct_despesas DOUBLE NOT NULL, custo_fixo DOUBLE NOT NULL);
CREATE TABLE IF NOT EXISTS skus (
    sku VARCHAR PRIMARY KEY, categoria VARCHAR, custo DOUBLE NOT NULL CHECK (custo > 0));
CREATE TABLE IF NOT EXISTS vendas (
    sku VARCHAR NOT NULL, canal VARCHAR NOT NULL, mes VARCHAR NOT NULL,
    unidades BIGINT NOT NULL CHECK (unidades > 0), preco DOUBLE NOT NULL CHECK (preco > 0),
    lote_id VARCHAR NOT NULL, PRIMARY KEY (sku, canal, mes));
CREATE TABLE IF NOT EXISTS quarentena (
    lote_id VARCHAR, tabela VARCHAR, motivo VARCHAR, linha_json VARCHAR);
CREATE TABLE IF NOT EXISTS execucoes (
    lote_id VARCHAR, tabela VARCHAR, executado_em TIMESTAMP, status VARCHAR,
    linhas_entrada BIGINT, linhas_carregadas BIGINT, linhas_quarentena BIGINT,
    inseridas BIGINT, atualizadas BIGINT);
"""


class QualidadeError(RuntimeError):
    """O lote reprovou nos limites de qualidade; nada foi carregado."""


@dataclass(frozen=True)
class ResumoCarga:
    lote_id: str
    status: str  # ok | ignorado_idempotente
    linhas_entrada: int
    linhas_carregadas: int
    linhas_quarentena: int
    inseridas: int
    atualizadas: int


def hash_lote(df: pd.DataFrame) -> str:
    """Identidade do lote = hash do conteúdo, independente da ordem das linhas."""
    canonico = df.sort_values(list(df.columns)).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:16]


class Armazem:
    def __init__(self, caminho: str | Path = ":memory:") -> None:
        self.caminho = str(caminho)
        self.con = duckdb.connect(self.caminho)
        self.con.execute(_DDL)

    def fechar(self) -> None:
        self.con.close()

    # ---- dimensões -------------------------------------------------------------
    def carregar_canais(self, canais: pd.DataFrame) -> None:
        for r in canais[["canal", "pct_despesas", "custo_fixo"]].itertuples(index=False):
            self.con.execute(
                "INSERT INTO canais VALUES (?, ?, ?) ON CONFLICT (canal) DO UPDATE SET "
                "pct_despesas = excluded.pct_despesas, custo_fixo = excluded.custo_fixo",
                list(r),
            )

    def carregar_skus(self, skus: pd.DataFrame, agora: datetime | None = None) -> ResumoCarga:
        res = validar_skus(skus)
        lote = hash_lote(skus[["sku", "categoria", "custo"]])
        if self._ja_executado(lote, "skus"):
            return self._resumo_ignorado(lote, len(skus))
        existentes = self._contar_existentes("skus", res.validas[["sku"]], ["sku"])
        self.con.execute("BEGIN")
        try:
            self._quarentenar(lote, "skus", res.rejeitadas)
            if len(res.validas):
                self.con.register("_s", res.validas)
                self.con.execute(
                    "INSERT INTO skus SELECT sku, categoria, custo FROM _s "
                    "ON CONFLICT (sku) DO UPDATE SET categoria = excluded.categoria, "
                    "custo = excluded.custo"
                )
                self.con.unregister("_s")
            resumo = self._fechar_execucao(lote, "skus", len(skus), res, existentes, agora)
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        return resumo

    # ---- fato ------------------------------------------------------------------
    def carregar_vendas(
        self,
        vendas: pd.DataFrame,
        *,
        limite_rejeicao: float = 0.05,
        queda_max_volume: float = 0.5,
        agora: datetime | None = None,
    ) -> ResumoCarga:
        """Carrega um lote de vendas.

        ``limite_rejeicao``: fração máxima de linhas em quarentena; acima disso o lote
        inteiro é bloqueado. ``queda_max_volume``: o lote não pode ter menos que
        (1 - queda_max_volume) do volume do último lote aceito (baseline de contagem).
        """
        skus = {r[0] for r in self.con.execute("SELECT sku FROM skus").fetchall()}
        canais = {r[0] for r in self.con.execute("SELECT canal FROM canais").fetchall()}
        res = validar_vendas(vendas, skus, canais)
        lote = hash_lote(vendas[["sku", "canal", "mes", "unidades", "preco"]])
        if self._ja_executado(lote, "vendas"):
            evento("lote_ignorado_idempotente", lote_id=lote, tabela="vendas")
            return self._resumo_ignorado(lote, len(vendas))

        if res.taxa_rejeicao > limite_rejeicao:
            self._registrar_bloqueio(lote, vendas, res, agora)
            raise QualidadeError(
                f"lote {lote}: {res.taxa_rejeicao:.1%} das linhas rejeitadas "
                f"(limite {limite_rejeicao:.1%}); nada foi carregado"
            )
        base = self._ultimo_volume_aceito()
        if base is not None and len(res.validas) < base * (1 - queda_max_volume):
            self._registrar_bloqueio(lote, vendas, res, agora)
            raise QualidadeError(
                f"lote {lote}: {len(res.validas)} linhas válidas contra baseline {base} "
                f"(queda máxima {queda_max_volume:.0%}); nada foi carregado"
            )

        existentes = self._contar_existentes("vendas", res.validas[CHAVE_VENDAS], CHAVE_VENDAS)
        self.con.execute("BEGIN")
        try:
            self._quarentenar(lote, "vendas", res.rejeitadas)
            if len(res.validas):
                self.con.register("_v", res.validas.assign(lote_id=lote))
                self.con.execute(
                    "INSERT INTO vendas SELECT sku, canal, mes, CAST(unidades AS BIGINT), "
                    "preco, lote_id FROM _v ON CONFLICT (sku, canal, mes) DO UPDATE SET "
                    "unidades = excluded.unidades, preco = excluded.preco, "
                    "lote_id = excluded.lote_id"
                )
                self.con.unregister("_v")
            resumo = self._fechar_execucao(lote, "vendas", len(vendas), res, existentes, agora)
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        evento("lote_carregado", **asdict(resumo))
        return resumo

    # ---- consulta --------------------------------------------------------------
    def tabelas_para_analise(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        v = self.con.execute("SELECT sku, canal, mes, unidades, preco FROM vendas").df()
        s = self.con.execute("SELECT sku, categoria, custo FROM skus").df()
        c = self.con.execute("SELECT canal, pct_despesas, custo_fixo FROM canais").df()
        return v, s, c

    def linhagem(self) -> pd.DataFrame:
        """Quantas linhas vivas na tabela de vendas vieram de cada lote."""
        return self.con.execute(
            "SELECT lote_id, count(*) AS linhas_vivas FROM vendas GROUP BY lote_id ORDER BY 1"
        ).df()

    def impressao_digital(self) -> str:
        """Hash do estado das tabelas de negócio (usado para provar que algo é só leitura)."""
        h = hashlib.sha256()
        for t, ordem in (("vendas", "sku, canal, mes"), ("skus", "sku"), ("canais", "canal")):
            df = self.con.execute(f"SELECT * FROM {t} ORDER BY {ordem}").df()
            h.update(df.to_csv(index=False).encode("utf-8"))
        return h.hexdigest()[:16]

    # ---- internos --------------------------------------------------------------
    def escalar(self, sql: str, params: list | None = None) -> Any:
        linha = self.con.execute(sql, params or []).fetchone()
        assert linha is not None, "consulta escalar sem linha"
        return linha[0]

    def _ja_executado(self, lote: str, tabela: str) -> bool:
        n = self.escalar(
            "SELECT count(*) FROM execucoes WHERE lote_id = ? AND tabela = ? AND status = 'ok'",
            [lote, tabela],
        )
        return bool(n > 0)

    @staticmethod
    def _resumo_ignorado(lote: str, entrada: int) -> ResumoCarga:
        return ResumoCarga(lote, "ignorado_idempotente", entrada, 0, 0, 0, 0)

    def _contar_existentes(self, tabela: str, chaves: pd.DataFrame, cols: list[str]) -> int:
        if chaves.empty:
            return 0
        self.con.register("_k", chaves)
        cond = " AND ".join(f"t.{c} = k.{c}" for c in cols)
        n = self.escalar(
            f"SELECT count(*) FROM _k k WHERE EXISTS (SELECT 1 FROM {tabela} t WHERE {cond})"
        )
        self.con.unregister("_k")
        return int(n)

    def _ultimo_volume_aceito(self) -> int | None:
        r = self.con.execute(
            "SELECT linhas_carregadas FROM execucoes WHERE tabela = 'vendas' AND status = 'ok' "
            "AND linhas_carregadas > 0 ORDER BY executado_em DESC, rowid DESC LIMIT 1"
        ).fetchone()
        return None if r is None else int(r[0])

    def _quarentenar(self, lote: str, tabela: str, rej: pd.DataFrame) -> None:
        for linha in rej.to_dict("records"):
            motivo = linha.pop("motivo")
            self.con.execute(
                "INSERT INTO quarentena VALUES (?, ?, ?, ?)",
                [lote, tabela, motivo, json.dumps(linha, ensure_ascii=False, default=str)],
            )

    def _fechar_execucao(self, lote, tabela, entrada, res, existentes, agora) -> ResumoCarga:
        carregadas, quarentena = len(res.validas), len(res.rejeitadas)
        assert entrada == carregadas + quarentena, "invariante: entrada = carregadas + quarentena"
        ts = (agora or datetime.now(UTC)).replace(tzinfo=None)
        resumo = ResumoCarga(
            lote, "ok", entrada, carregadas, quarentena, carregadas - existentes, existentes
        )
        self.con.execute(
            "INSERT INTO execucoes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                lote,
                tabela,
                ts,
                "ok",
                entrada,
                carregadas,
                quarentena,
                resumo.inseridas,
                resumo.atualizadas,
            ],
        )
        return resumo

    def _registrar_bloqueio(self, lote, vendas, res, agora) -> None:
        ts = (agora or datetime.now(UTC)).replace(tzinfo=None)
        self._quarentenar(lote, "vendas", res.rejeitadas)
        self.con.execute(
            "INSERT INTO execucoes VALUES (?, 'vendas', ?, 'bloqueado_qualidade', ?, 0, ?, 0, 0)",
            [lote, ts, len(vendas), len(res.rejeitadas)],
        )
        evento("lote_bloqueado", 30, lote_id=lote, taxa_rejeicao=round(res.taxa_rejeicao, 4))
