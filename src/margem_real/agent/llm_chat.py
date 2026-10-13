"""Planejador para APIs no formato "chat completions" (GitHub Models, Gemini, Groq, OpenRouter...).

Mesmo contrato do ``PlanejadorClaude``: 6 ferramentas ``margem_*`` somente leitura mais
``responder``. Existe para permitir uma avaliação SEM custo: o GitHub Models aceita o
``GITHUB_TOKEN`` do próprio GitHub Actions (permissão ``models: read``), sem chave a guardar.

NADA aqui foi validado contra um modelo real até o registro em VERIFICACAO.md dizer o contrário;
os testes usam um cliente falso. O limite gratuito do GitHub Models é pequeno
(ver docs/AVALIACAO.md).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from .agent import Passo, Resposta
from .llm import SISTEMA, STATUS_VALIDOS, Cliente, Uso, ferramentas_para_api

URL_GITHUB = "https://models.github.ai/inference/chat/completions"


def ferramentas_chat() -> list[dict[str, Any]]:
    """As ferramentas no formato ``tools`` do chat completions."""
    return [
        {
            "type": "function",
            "function": {
                "name": f["name"],
                "description": f["description"],
                "parameters": f["input_schema"],
            },
        }
        for f in ferramentas_para_api()
    ]


def cliente_chat_http(
    url: str, token: str, tentativas: int = 4, espera: float = 5.0, extra: dict | None = None
) -> Cliente:
    """Cliente mínimo (urllib) com repetição em 429/5xx. O token nunca aparece em erros."""

    def chamar(corpo: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=json.dumps(corpo).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                **(extra or {}),
            },
        )
        for i in range(tentativas):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and i < tentativas - 1:
                    time.sleep(espera * (2**i))
                    continue
                raise RuntimeError(f"API respondeu HTTP {e.code}") from None
        raise RuntimeError("sem resposta da API")  # pragma: no cover

    return chamar


def cliente_github(token: str | None = None) -> Cliente:
    t = token or os.environ.get("GITHUB_TOKEN")
    if not t:
        raise RuntimeError("GITHUB_TOKEN ausente (no Actions: permissions: models: read).")
    return cliente_chat_http(
        URL_GITHUB,
        t,
        extra={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )


class PlanejadorChat:
    """Um LLM de API "chat completions" como ``Planejador`` (conversa reconstruída do histórico)."""

    def __init__(
        self,
        modelo: str,
        cliente: Cliente,
        max_tokens: int = 1024,
        temperatura: float | None = None,
        uso: Uso | None = None,
    ) -> None:
        self.modelo = modelo
        self.cliente = cliente
        self.max_tokens = max_tokens
        self.temperatura = temperatura
        self.uso = uso if uso is not None else Uso()

    def _mensagens(self, pergunta: str, historico: list[dict]) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": pergunta},
        ]
        for i, h in enumerate(historico):
            tid = f"call_{i:02d}"
            msgs.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tid,
                            "type": "function",
                            "function": {
                                "name": h["ferramenta"],
                                "arguments": json.dumps(h["args"], ensure_ascii=False),
                            },
                        }
                    ],
                }
            )
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": tid,
                    "content": json.dumps(h["resultado"], ensure_ascii=False, default=str),
                }
            )
        return msgs

    def proximo(self, pergunta: str, historico: list[dict]) -> Passo:
        corpo: dict[str, Any] = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "tools": ferramentas_chat(),
            "tool_choice": "required",
            "messages": self._mensagens(pergunta, historico),
        }
        if self.temperatura is not None:
            corpo["temperature"] = self.temperatura
        t0 = time.monotonic()
        r = self.cliente(corpo)
        self.uso.segundos += time.monotonic() - t0
        self.uso.chamadas += 1
        u = r.get("usage") or {}
        self.uso.tokens_entrada += int(u.get("prompt_tokens", 0))
        self.uso.tokens_saida += int(u.get("completion_tokens", 0))
        return _para_passo_chat(r)


def _para_passo_chat(resp: dict[str, Any]) -> Passo:
    escolhas = resp.get("choices") or []
    msg = (escolhas[0].get("message") if escolhas else None) or {}
    chamadas = msg.get("tool_calls") or []
    if not chamadas:
        return Passo(resposta=Resposta("erro", "modelo não chamou nenhuma ferramenta"))
    fn = chamadas[0].get("function") or {}
    nome = fn.get("name", "")
    try:
        args = json.loads(fn.get("arguments") or "{}")
    except json.JSONDecodeError:
        return Passo(resposta=Resposta("erro", "argumentos da ferramenta não são JSON válido"))
    if not isinstance(args, dict):
        args = {}
    if nome != "responder":
        return Passo(nome, args)
    status = args.get("status")
    if status not in STATUS_VALIDOS:
        return Passo(resposta=Resposta("erro", f"status inválido do modelo: {status!r}"))
    bruto = args.get("dados")
    dados: dict[str, Any] = bruto if isinstance(bruto, dict) else {}
    return Passo(resposta=Resposta(status, str(args.get("texto", "")), dados))
