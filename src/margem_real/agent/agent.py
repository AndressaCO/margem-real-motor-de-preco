"""Laço do agente: planeja -> chama ferramenta -> observa -> responde. Registra transcrição."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from .tools import Ferramentas

Status = Literal["ok", "recusa", "esclarecimento", "erro"]
MAX_PASSOS = 6


@dataclass(frozen=True)
class Resposta:
    status: Status
    texto: str
    dados: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Passo:
    """Decisão do planejador: chamar uma ferramenta OU responder."""

    ferramenta: str | None = None
    args: dict = field(default_factory=dict)
    resposta: Resposta | None = None


class Planejador(Protocol):
    """Interface plugável. Um LLM entra aqui; o harness de avaliação não muda."""

    def proximo(self, pergunta: str, historico: list[dict]) -> Passo: ...


@dataclass(frozen=True)
class Execucao:
    resposta: Resposta
    transcricao: list[dict]

    @property
    def chamadas(self) -> list[dict]:
        return [e for e in self.transcricao if e["tipo"] == "chamada"]


def executar(pergunta: str, planejador: Planejador, ferramentas: Ferramentas) -> Execucao:
    trans: list[dict] = [{"tipo": "pergunta", "texto": pergunta}]
    historico: list[dict] = []
    for _ in range(MAX_PASSOS):
        passo = planejador.proximo(pergunta, historico)
        if passo.resposta is not None:
            r = passo.resposta
            trans.append(
                {"tipo": "resposta", "status": r.status, "texto": r.texto, "dados": r.dados}
            )
            return Execucao(r, trans)
        if passo.ferramenta is None:
            break
        trans.append({"tipo": "chamada", "ferramenta": passo.ferramenta, "args": passo.args})
        resultado = ferramentas.chamar(passo.ferramenta, passo.args)
        trans.append({"tipo": "resultado", "ferramenta": passo.ferramenta, "resultado": resultado})
        historico.append(
            {"ferramenta": passo.ferramenta, "args": passo.args, "resultado": resultado}
        )
    r = Resposta("erro", f"sem conclusão em {MAX_PASSOS} passos")
    trans.append({"tipo": "resposta", "status": r.status, "texto": r.texto, "dados": {}})
    return Execucao(r, trans)
