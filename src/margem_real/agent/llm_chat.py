"""Planejador para APIs no formato "chat completions" (Gemini, Groq, OpenRouter...).

Mesmo contrato do ``PlanejadorClaude``: 6 ferramentas ``margem_*`` somente leitura mais
``responder``. Existe para permitir uma avaliação sem custo no plano gratuito do Gemini
(chave gratuita do Google AI Studio). O GitHub Models foi tentado primeiro e NÃO funciona mais:
responde 200 "OK" em texto simples e a documentação o dá como encerrado em 30/07/2026.

NADA aqui foi validado contra um modelo real até o registro em VERIFICACAO.md dizer o contrário;
os testes usam um cliente falso. Limites do plano gratuito: ver docs/AVALIACAO.md.
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

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"


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


def _corpo_erro(e: urllib.error.HTTPError, segredo: str) -> str:
    """Trecho do corpo do erro (ajuda a achar o campo recusado), sem o segredo."""
    try:
        txt = e.read()[:400].decode("utf-8", "replace")
    except Exception:
        return "(sem corpo)"
    return " ".join(txt.replace(segredo, "***").split())


def cliente_chat_http(
    url: str,
    token: str,
    tentativas: int = 4,
    espera: float = 5.0,
    extra: dict | None = None,
    timeout: float = 90.0,
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
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    bruto = r.read()
                    tipo = r.headers.get("Content-Type") if hasattr(r, "headers") else None
                    url_final = r.geturl() if hasattr(r, "geturl") else url
                    meta = f"HTTP {getattr(r, 'status', '?')}, {tipo}, {url_final}"
                try:
                    return json.loads(bruto)
                except json.JSONDecodeError:
                    trecho = bruto[:200].decode("utf-8", "replace")
                    raise RuntimeError(f"resposta não é JSON ({meta}): {trecho!r}") from None
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and i < tentativas - 1:
                    time.sleep(espera * (2**i))
                    continue
                raise RuntimeError(
                    f"API respondeu HTTP {e.code}: {_corpo_erro(e, token)}"
                ) from None
            except (TimeoutError, urllib.error.URLError) as e:
                if i < tentativas - 1:
                    time.sleep(espera * (2**i))
                    continue
                raise RuntimeError(
                    f"sem resposta da API após {tentativas} tentativas ({type(e).__name__})"
                ) from None
        raise RuntimeError("sem resposta da API")  # pragma: no cover

    return chamar


def cliente_gemini(chave: str | None = None) -> Cliente:
    k = chave or os.environ.get("GEMINI_API_KEY")
    if not k:
        raise RuntimeError("GEMINI_API_KEY ausente (chave gratuita em aistudio.google.com).")
    return cliente_chat_http(URL_GEMINI, k)


class PlanejadorChat:
    """Um LLM de API "chat completions" como ``Planejador`` (conversa reconstruída do histórico)."""

    def __init__(
        self,
        modelo: str,
        cliente: Cliente,
        max_tokens: int = 1024,
        temperatura: float | None = None,
        uso: Uso | None = None,
        tool_choice: str = "required",
    ) -> None:
        self.tool_choice = tool_choice
        self.modelo = modelo
        self.cliente = cliente
        self.max_tokens = max_tokens
        self.temperatura = temperatura
        self.uso = uso if uso is not None else Uso()
        # Gemini 3 exige devolver a "thought_signature" (extra_content) de cada chamada
        # de ferramenta nas voltas seguintes; guardamos uma por passo (índice do histórico).
        self._extras: list[dict[str, Any] | None] = []

    def _mensagens(self, pergunta: str, historico: list[dict]) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": pergunta},
        ]
        for i, h in enumerate(historico):
            tid = f"call_{i:02d}"
            chamada: dict[str, Any] = {
                "id": tid,
                "type": "function",
                "function": {
                    "name": h["ferramenta"],
                    "arguments": json.dumps(h["args"], ensure_ascii=False),
                },
            }
            if i < len(self._extras) and self._extras[i]:
                chamada["extra_content"] = self._extras[i]
            msgs.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [chamada],
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
            "tool_choice": self.tool_choice,
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
        passo = _para_passo_chat(r)
        if passo.ferramenta:
            chamadas = ((r.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
            self._extras.append(chamadas[0].get("extra_content") if chamadas else None)
        return passo


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
