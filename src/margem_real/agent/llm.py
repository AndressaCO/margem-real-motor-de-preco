"""Planejador baseado em LLM (API Messages da Anthropic), sem dependência extra.

``PlanejadorClaude`` implementa o mesmo ``Planejador`` do stand-in de regras: o harness de
avaliação, as ferramentas e os avaliadores não mudam. O modelo vê as 6 ferramentas
``margem_*`` e uma 7ª, ``responder``, que encerra a conversa com um status e dados
estruturados (é o que os avaliadores por estado final conferem).

Segurança: as ferramentas são somente leitura; a chave vem de ``ANTHROPIC_API_KEY`` e nunca é
gravada em transcrição, relatório ou log.

O ``PlanejadorClaude`` (API da Anthropic) NÃO foi executado contra a API real (sem chave):
os testes usam um cliente falso. Rode ``avaliar-llm`` (workflow do GitHub) para obter números reais.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .agent import Passo, Resposta
from .tools import ESPECIFICACOES

URL = "https://api.anthropic.com/v1/messages"
VERSAO_API = "2023-06-01"
STATUS_VALIDOS = ("ok", "recusa", "esclarecimento", "erro")

SISTEMA = (
    "Você é um agente de análise de margem de contribuição por SKU e canal, em português. "
    "Use SOMENTE as ferramentas fornecidas; elas são somente leitura. Nunca invente números: "
    "todo valor da resposta deve vir do resultado de uma ferramenta ou do enunciado. "
    "Se faltar um dado obrigatório, responda com status 'esclarecimento' e liste o que falta "
    "em dados.faltam. Se o pedido exigir alterar preços, dados ou sistemas, ou estiver fora do "
    "escopo (margem, preço mínimo/sugerido, conciliação), responda com status 'recusa'. "
    "Se uma ferramenta devolver erro, responda com status 'erro'. Para finalizar, chame SEMPRE "
    "a ferramenta `responder` com status, texto curto e dados (chaves numéricas em fração ou "
    "reais, como a ferramenta devolveu)."
)

ESPECIFICACAO_RESPONDER: dict[str, Any] = {
    "name": "responder",
    "description": (
        "Encerra o atendimento. status: ok | recusa | esclarecimento | erro. texto: resposta "
        "curta. dados: objeto com os valores-chave devolvidos pelas ferramentas (por exemplo "
        "preco_minimo, preco_sugerido, canal, margem_pct, total, aprovado, sku, faltam)."
    ),
    "input_schema": {
        "properties": {
            "status": {"type": "string", "enum": list(STATUS_VALIDOS)},
            "texto": {"type": "string"},
            "dados": {"type": "object"},
        },
        "required": ["status", "texto"],
    },
}

Cliente = Callable[[dict[str, Any]], dict[str, Any]]


def ferramentas_para_api() -> list[dict[str, Any]]:
    """ESPECIFICACOES no formato da API (input_schema precisa de ``type: object``)."""
    out = []
    for spec in [*ESPECIFICACOES, ESPECIFICACAO_RESPONDER]:
        schema = {"type": "object", **spec["input_schema"]}
        out.append(
            {"name": spec["name"], "description": spec["description"], "input_schema": schema}
        )
    return out


def cliente_http(chave: str | None = None, tentativas: int = 4, espera: float = 2.0) -> Cliente:
    """Cliente mínimo (urllib) com repetição para 429/5xx. A chave nunca é exibida em erros."""
    k = chave or os.environ.get("ANTHROPIC_API_KEY")
    if not k:
        raise RuntimeError(
            "ANTHROPIC_API_KEY ausente: defina a variável de ambiente (ou o secret no GitHub)."
        )

    def chamar(corpo: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            URL,
            data=json.dumps(corpo).encode("utf-8"),
            headers={
                "x-api-key": k,
                "anthropic-version": VERSAO_API,
                "content-type": "application/json",
            },
        )
        for i in range(tentativas):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 529) and i < tentativas - 1:
                    time.sleep(espera * (2**i))
                    continue
                raise RuntimeError(f"API respondeu HTTP {e.code}") from None
        raise RuntimeError("sem resposta da API")  # pragma: no cover

    return chamar


@dataclass
class Uso:
    chamadas: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    segundos: float = 0.0


class PlanejadorClaude:
    """Um LLM como ``Planejador``: reconstrói a conversa a cada passo a partir do histórico."""

    def __init__(
        self,
        modelo: str,
        cliente: Cliente | None = None,
        max_tokens: int = 1024,
        temperatura: float | None = None,
        uso: Uso | None = None,
    ) -> None:
        self.modelo = modelo
        self.cliente = cliente or cliente_http()
        self.max_tokens = max_tokens
        self.temperatura = temperatura
        self.uso = uso if uso is not None else Uso()

    def _mensagens(self, pergunta: str, historico: list[dict]) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [{"role": "user", "content": pergunta}]
        for i, h in enumerate(historico):
            tid = f"toolu_{i:02d}"
            msgs.append(
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tid, "name": h["ferramenta"], "input": h["args"]}
                    ],
                }
            )
            msgs.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "content": json.dumps(h["resultado"], ensure_ascii=False, default=str),
                        }
                    ],
                }
            )
        return msgs

    def proximo(self, pergunta: str, historico: list[dict]) -> Passo:
        corpo: dict[str, Any] = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "system": SISTEMA,
            "tools": ferramentas_para_api(),
            "tool_choice": {"type": "any"},  # sempre uma ferramenta; `responder` encerra
            "messages": self._mensagens(pergunta, historico),
        }
        if self.temperatura is not None:
            corpo["temperature"] = self.temperatura
        t0 = time.monotonic()
        r = self.cliente(corpo)
        self.uso.segundos += time.monotonic() - t0
        self.uso.chamadas += 1
        u = r.get("usage", {})
        self.uso.tokens_entrada += int(u.get("input_tokens", 0))
        self.uso.tokens_saida += int(u.get("output_tokens", 0))
        return _para_passo(r)


def _para_passo(resp: dict[str, Any]) -> Passo:
    uso_ferramenta = next((b for b in resp.get("content", []) if b.get("type") == "tool_use"), None)
    if uso_ferramenta is None:
        return Passo(resposta=Resposta("erro", "modelo não chamou nenhuma ferramenta"))
    nome, args = uso_ferramenta["name"], uso_ferramenta.get("input") or {}
    if nome != "responder":
        return Passo(nome, args)
    status = args.get("status")
    if status not in STATUS_VALIDOS:
        return Passo(resposta=Resposta("erro", f"status inválido do modelo: {status!r}"))
    bruto = args.get("dados")
    dados: dict[str, Any] = bruto if isinstance(bruto, dict) else {}
    return Passo(resposta=Resposta(status, str(args.get("texto", "")), dados))
