"""Ferramentas do agente.

Princípios (extraídos de guias públicos de escrita de ferramentas para agentes; ver
docs/BENCHMARK.md): poucas ferramentas, cada uma com um propósito; nomes com prefixo comum;
descrições escritas como para uma pessoa nova no time (dizem QUANDO usar e QUANDO NÃO);
schema estrito (campo desconhecido é erro); resposta com alto sinal e tamanho controlado
(paginação/truncamento com instrução de como refinar); erros acionáveis; TODAS somente leitura.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..analysis import abaixo_do_minimo, margem_por_sku_canal, resumo_por_canal
from ..pipeline import Armazem, conciliar
from ..pricing import preco_minimo, preco_sugerido

LIMITE_MAXIMO = 20

ESPECIFICACOES: list[dict[str, Any]] = [
    {
        "name": "margem_resumo_por_canal",
        "description": (
            "Margem de contribuição agregada por canal de venda (receita, margem em R$ e em %, "
            "e fração de pares SKU x canal vendendo no prejuízo). Use para comparar canais ou "
            "achar o canal mais frágil. NÃO use para um SKU específico (use "
            "margem_reprecificar_par) nem para listar SKUs (use margem_pares_no_prejuizo)."
        ),
        "input_schema": {"properties": {}, "required": []},
    },
    {
        "name": "margem_pares_no_prejuizo",
        "description": (
            "Lista os pares SKU x canal cujo preço médio praticado está abaixo do preço mínimo "
            "(vendem com margem de contribuição negativa), do pior para o melhor. Devolve "
            f"`total` (sempre completo) e no máximo `limite` itens (máx. {LIMITE_MAXIMO}). Se "
            "`truncado` for true, refine com `canal`. NÃO use para calcular preço de um item "
            "novo (use as ferramentas margem_calcular_*)."
        ),
        "input_schema": {
            "properties": {
                "canal": {"type": "string", "description": "Nome exato do canal (opcional)."},
                "limite": {"type": "integer", "description": f"1 a {LIMITE_MAXIMO}; padrão 5."},
            },
            "required": [],
        },
    },
    {
        "name": "margem_calcular_preco_minimo",
        "description": (
            "Preço de equilíbrio (margem de contribuição zero) = (custo + custo_fixo) / "
            "(1 - pct_despesas), arredondado PARA CIMA ao centavo. `pct_despesas` é FRAÇÃO "
            "(34% = 0.34) e soma imposto, comissão, frete, devolução e CAC. Use quando o "
            "usuário informar custo e despesas. NÃO use se os valores estão no armazém: "
            "use margem_reprecificar_par."
        ),
        "input_schema": {
            "properties": {
                "custo": {"type": "number", "description": "Custo unitário em R$ (>= 0)."},
                "pct_despesas": {"type": "number", "description": "Fração em [0, 1)."},
                "custo_fixo": {"type": "number", "description": "R$ por unidade; padrão 0."},
            },
            "required": ["custo", "pct_despesas"],
        },
    },
    {
        "name": "margem_calcular_preco_sugerido",
        "description": (
            "Preço que entrega a margem líquida alvo = (custo + custo_fixo) / "
            "(1 - pct_despesas - margem_alvo), arredondado PARA CIMA ao centavo. Frações, não "
            "porcentagens. Exige pct_despesas + margem_alvo < 1. NÃO modela elasticidade."
        ),
        "input_schema": {
            "properties": {
                "custo": {"type": "number", "description": "Custo unitário em R$ (>= 0)."},
                "pct_despesas": {"type": "number", "description": "Fração em [0, 1)."},
                "margem_alvo": {"type": "number", "description": "Fração em [0, 1)."},
                "custo_fixo": {"type": "number", "description": "R$ por unidade; padrão 0."},
            },
            "required": ["custo", "pct_despesas", "margem_alvo"],
        },
    },
    {
        "name": "margem_reprecificar_par",
        "description": (
            "Para UM par SKU x canal já existente no armazém, devolve preço médio praticado, "
            "preço mínimo, preço sugerido para `margem_alvo` e a variação percentual necessária. "
            "Os parâmetros do canal vêm do armazém. NÃO altera nenhum preço: só calcula."
        ),
        "input_schema": {
            "properties": {
                "sku": {"type": "string", "description": "Ex.: SKU-0007."},
                "canal": {"type": "string", "description": "Nome exato do canal."},
                "margem_alvo": {"type": "number", "description": "Fração em [0, 1)."},
            },
            "required": ["sku", "canal", "margem_alvo"],
        },
    },
    {
        "name": "margem_conciliar",
        "description": (
            "Controle de totais: concilia receita e unidades da camada bruta com a camada de "
            "consumo. Use quando perguntarem se os números fecham/conferem. Somente leitura."
        ),
        "input_schema": {"properties": {}, "required": []},
    },
]

_TIPOS = {"number": (int, float), "integer": (int,), "string": (str,)}


def _erro(msg: str, como: str) -> dict:
    return {"ok": False, "erro": msg, "como_corrigir": como}


def validar_args(nome: str, args: dict) -> dict | None:
    """Schema estrito: devolve um erro acionável ou None."""
    spec = next((s for s in ESPECIFICACOES if s["name"] == nome), None)
    if spec is None:
        validos = ", ".join(s["name"] for s in ESPECIFICACOES)
        return _erro(f"ferramenta desconhecida: {nome}", f"use uma de: {validos}")
    props, obrig = spec["input_schema"]["properties"], spec["input_schema"]["required"]
    extras = sorted(set(args) - set(props))
    if extras:
        return _erro(f"argumentos desconhecidos: {extras}", f"permitidos: {sorted(props)}")
    faltam = [r for r in obrig if r not in args]
    if faltam:
        return _erro(f"argumentos obrigatórios ausentes: {faltam}", "peça o dado ao usuário")
    for k, v in args.items():
        ok = isinstance(v, _TIPOS[props[k]["type"]]) and not isinstance(v, bool)
        if not ok:
            return _erro(
                f"{k}: esperado {props[k]['type']}, veio {type(v).__name__}", "corrija o tipo"
            )
    return None


class Ferramentas:
    """Executa as ferramentas contra um Armazem. Nunca escreve."""

    def __init__(self, armazem: Armazem) -> None:
        self.armazem = armazem
        v, s, c = armazem.tabelas_para_analise()
        self._canais = c
        self._skus = set(s["sku"])
        self._margem: pd.DataFrame = margem_por_sku_canal(v, s, c)

    def chamar(self, nome: str, args: dict | None = None) -> dict:
        args = args or {}
        problema = validar_args(nome, args)
        if problema:
            return problema
        try:
            return getattr(self, f"_{nome}")(**args)
        except ValueError as e:  # regras de preço (pricing._validar)
            return _erro(str(e), "use frações (34% = 0.34) e garanta despesas + margem < 1")

    # ---- implementações -------------------------------------------------------------
    def _margem_resumo_por_canal(self) -> dict:
        r = resumo_por_canal(self._margem)
        itens = [
            {
                "canal": x["canal"],
                "receita": round(float(x["receita"]), 2),
                "margem_contribuicao": round(float(x["margem_contribuicao"]), 2),
                "margem_pct": round(float(x["margem_pct"]), 4),
                "pct_pares_no_prejuizo": round(float(x["pct_pares_no_prejuizo"]), 4),
            }
            for x in r.to_dict("records")
        ]
        return {"ok": True, "canais": itens, "ordenado_por": "margem_pct crescente"}

    def _margem_pares_no_prejuizo(self, canal: str | None = None, limite: int = 5) -> dict:
        if canal is not None and canal not in set(self._canais["canal"]):
            return _erro(
                f"canal inexistente: {canal}",
                f"canais válidos: {sorted(self._canais['canal'])}",
            )
        if not (1 <= limite <= LIMITE_MAXIMO):
            return _erro(f"limite fora de [1, {LIMITE_MAXIMO}]", "ajuste `limite`")
        d = abaixo_do_minimo(self._margem)
        if canal:
            d = d[d["canal"] == canal]
        d = d.sort_values(["margem_contribuicao", "sku", "canal"])
        itens = [
            {
                "sku": x["sku"],
                "canal": x["canal"],
                "margem_contribuicao": float(x["margem_contribuicao"]),
                "preco_medio_praticado": float(x["preco_medio_praticado"]),
                "preco_minimo": float(x["preco_minimo"]),
            }
            for x in d.head(limite).to_dict("records")
        ]
        return {
            "ok": True,
            "total": int(len(d)),
            "retornados": len(itens),
            "truncado": len(d) > len(itens),
            "itens": itens,
        }

    def _margem_calcular_preco_minimo(
        self, custo: float, pct_despesas: float, custo_fixo: float = 0.0
    ) -> dict:
        return {"ok": True, "preco_minimo": preco_minimo(custo, pct_despesas, custo_fixo)}

    def _margem_calcular_preco_sugerido(
        self, custo: float, pct_despesas: float, margem_alvo: float, custo_fixo: float = 0.0
    ) -> dict:
        return {
            "ok": True,
            "preco_sugerido": preco_sugerido(custo, pct_despesas, margem_alvo, custo_fixo),
        }

    def _margem_reprecificar_par(self, sku: str, canal: str, margem_alvo: float) -> dict:
        if sku not in self._skus:
            return _erro(f"sku inexistente: {sku}", "confira o código (formato SKU-0001)")
        if canal not in set(self._canais["canal"]):
            return _erro(f"canal inexistente: {canal}", f"válidos: {sorted(self._canais['canal'])}")
        linha = self._margem[(self._margem["sku"] == sku) & (self._margem["canal"] == canal)]
        if linha.empty:
            return _erro(
                f"o SKU {sku} não tem vendas no canal {canal}",
                "use margem_calcular_preco_sugerido informando custo e despesas",
            )
        r = linha.iloc[0]
        ch = self._canais[self._canais["canal"] == canal].iloc[0]
        sug = preco_sugerido(
            float(r["custo"]), float(ch["pct_despesas"]), margem_alvo, float(ch["custo_fixo"])
        )
        pr = float(r["preco_medio_praticado"])
        return {
            "ok": True,
            "sku": sku,
            "canal": canal,
            "preco_medio_praticado": pr,
            "preco_minimo": float(r["preco_minimo"]),
            "preco_sugerido": sug,
            "variacao_pct": round(sug / pr - 1, 4),
        }

    def _margem_conciliar(self) -> dict:
        return {"ok": True, **conciliar(self.armazem)}
