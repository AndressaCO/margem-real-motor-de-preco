"""Planejadores.

``PlanejadorRegras`` é um stand-in DETERMINÍSTICO de um LLM: roteia por regras sobre texto
em português. Ele existe para que o harness de avaliação rode sem chave de API e para que
o repositório seja reproduzível. Não é um modelo e seus resultados NÃO medem nenhum modelo.

``PlanejadorRuidoso`` injeta falhas sintéticas (ferramenta errada, argumento errado,
resposta adulterada) com taxa conhecida. Serve para validar o harness: provar que as
métricas e os avaliadores de fato DETECTAM falhas (um avaliador que aprova tudo é inútil).
"""

from __future__ import annotations

import random
import re

from .agent import Passo, Resposta
from .tools import ESPECIFICACOES

_NUM = r"(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
_ESCRITA = re.compile(
    r"\b(altere|alterar|atualize|atualizar|grave|gravar|apague|exclua|delete|"
    r"publique|envie|aplique|aplicar)\b",
    re.I,
)
_CANAL = re.compile(r"\b(marketplace_a|marketplace_b|site_proprio|b2b_distribuicao)\b")
_SKU = re.compile(r"\b(SKU-\d{4})\b", re.I)


def _num(txt: str) -> float:
    t = txt.strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    return float(t)


def _primeiro(padrao: re.Pattern[str], texto: str) -> str | None:
    m = padrao.search(texto)
    return m.group(1) if m else None


def _achar(padrao: str, texto: str) -> float | None:
    m = re.search(padrao, texto, re.I)
    return _num(m.group(1)) if m else None


def _pct(padrao: str, texto: str) -> float | None:
    v = _achar(padrao + r"[^\d%]{0,25}" + _NUM + r"\s*%", texto)
    return None if v is None else v / 100


def _falta(*itens: tuple[str, object | None]) -> list[str]:
    return [nome for nome, v in itens if v is None]


class PlanejadorRegras:
    def proximo(self, pergunta: str, historico: list[dict]) -> Passo:
        if historico:
            return self._responder(pergunta, historico[-1])
        q = pergunta.lower()
        if _ESCRITA.search(pergunta):
            return Passo(
                resposta=Resposta(
                    "recusa",
                    "Só consigo calcular e consultar; não altero preços, dados nem sistemas.",
                )
            )
        if "concili" in q or "fecham" in q or "conferem" in q:
            return Passo("margem_conciliar", {})

        canal = _primeiro(_CANAL, pergunta)
        sku = _primeiro(_SKU, pergunta)
        custo = _achar(r"custo(?!\s*fixo)\s*(?:de|é|=)?\s*(?:R\$)?\s*" + _NUM, pergunta)
        fixo = _achar(r"custo\s*fixo\s*(?:de|é|=)?\s*(?:R\$)?\s*" + _NUM, pergunta)
        desp = _pct(r"despesas", pergunta)
        alvo = _pct(r"margem(?:\s*alvo|\s*líquida)?", pergunta)

        if "reprecif" in q or (sku and ("sugerid" in q or "preço" in q or "preco" in q)):
            faltam = _falta(("sku", sku), ("canal", canal), ("margem alvo", alvo))
            if faltam:
                return self._pedir(faltam)
            return Passo(
                "margem_reprecificar_par", {"sku": sku, "canal": canal, "margem_alvo": alvo}
            )

        if "sugerid" in q:
            faltam = _falta(("custo", custo), ("pct de despesas", desp), ("margem alvo", alvo))
            if faltam:
                return self._pedir(faltam)
            args = {"custo": custo, "pct_despesas": desp, "margem_alvo": alvo}
            if fixo is not None:
                args["custo_fixo"] = fixo
            return Passo("margem_calcular_preco_sugerido", args)

        if "mínimo" in q or "minimo" in q or "equilíbrio" in q:
            faltam = _falta(("custo", custo), ("pct de despesas", desp))
            if faltam:
                return self._pedir(faltam)
            args = {"custo": custo, "pct_despesas": desp}
            if fixo is not None:
                args["custo_fixo"] = fixo
            return Passo("margem_calcular_preco_minimo", args)

        if "prejuízo" in q or "prejuizo" in q or "abaixo do mínimo" in q:
            filtro: dict = {"limite": 1 if "pior" in q else 5}
            if canal:
                filtro["canal"] = canal
            return Passo("margem_pares_no_prejuizo", filtro)

        if "canal" in q and "margem" in q:
            return Passo("margem_resumo_por_canal", {})

        return Passo(
            resposta=Resposta(
                "recusa",
                "Pergunta fora do que sei fazer: margem, preço mínimo/sugerido, conciliação.",
            )
        )

    @staticmethod
    def _pedir(faltam: list[str]) -> Passo:
        return Passo(
            resposta=Resposta(
                "esclarecimento", f"Preciso de: {', '.join(faltam)}.", {"faltam": faltam}
            )
        )

    def _responder(self, pergunta: str, h: dict) -> Passo:
        r, nome, q = h["resultado"], h["ferramenta"], pergunta.lower()
        if not r.get("ok"):
            return Passo(resposta=Resposta("erro", f"{r['erro']} — {r['como_corrigir']}"))
        if nome == "margem_calcular_preco_minimo":
            d = {"preco_minimo": r["preco_minimo"]}
        elif nome == "margem_calcular_preco_sugerido":
            d = {"preco_sugerido": r["preco_sugerido"]}
        elif nome == "margem_reprecificar_par":
            d = {k: r[k] for k in ("preco_minimo", "preco_sugerido", "variacao_pct")}
        elif nome == "margem_conciliar":
            d = {"aprovado": r["aprovado"]}
        elif nome == "margem_pares_no_prejuizo":
            d = {"total": r["total"]}
            if "pior" in q and r["itens"]:
                d.update(sku=r["itens"][0]["sku"], canal=r["itens"][0]["canal"])
        else:  # resumo por canal
            canais = r["canais"]
            alvo = _primeiro(_CANAL, pergunta)
            if alvo:
                c = next(x for x in canais if x["canal"] == alvo)
                d = {"canal": alvo, "margem_pct": c["margem_pct"]}
            elif "maior" in q or "melhor" in q:
                d = {"canal": max(canais, key=lambda x: x["margem_pct"])["canal"]}
            else:
                d = {"canal": min(canais, key=lambda x: x["margem_pct"])["canal"]}
        return Passo(resposta=Resposta("ok", str(d), d))


class PlanejadorRuidoso:
    """Envolve outro planejador e o sabota com probabilidade ``p_erro`` por passo.

    Determinístico por (semente, pergunta, trial, passo): o mesmo trial sempre falha igual.
    """

    def __init__(self, base, p_erro: float, semente: int = 0, trial: int = 0) -> None:
        self.base, self.p, self.semente, self.trial = base, p_erro, semente, trial

    def proximo(self, pergunta: str, historico: list[dict]) -> Passo:
        rng = random.Random(f"{self.semente}|{pergunta}|{self.trial}|{len(historico)}")
        passo = self.base.proximo(pergunta, historico)
        if rng.random() >= self.p:
            return passo
        if passo.ferramenta:  # sabota a chamada: ferramenta errada OU argumento adulterado
            if rng.random() < 0.5:
                outra = rng.choice(
                    [s["name"] for s in ESPECIFICACOES if s["name"] != passo.ferramenta]
                )
                return Passo(outra, passo.args)
            args = {
                k: (v * 10 if isinstance(v, float) and v < 1 else v) for k, v in passo.args.items()
            }
            return Passo(passo.ferramenta, args)
        r = passo.resposta
        if r.status == "ok" and r.dados:  # sabota a resposta: número 5% maior / texto trocado
            d = {k: (round(v * 1.05, 4) if isinstance(v, float) else v) for k, v in r.dados.items()}
            return Passo(resposta=Resposta(r.status, str(d), d))
        return Passo(resposta=Resposta("ok", "tudo certo", {}))  # falso positivo: nunca recusa
