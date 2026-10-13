"""Testes do planejador LLM com cliente FALSO. Nenhum teste chama a API real."""

import json
import urllib.error

import pytest

from margem_real.agent import ESPECIFICACOES, PlanejadorChat, PlanejadorClaude, PlanejadorRegras
from margem_real.agent import llm as L
from margem_real.agent import llm_chat as C
from margem_real.agent.evals import __main__ as cli
from margem_real.agent.evals.llm_run import renderizar, rodar_llm


def _resp(*blocos, uso=(10, 5)):
    return {
        "content": list(blocos),
        "usage": {"input_tokens": uso[0], "output_tokens": uso[1]},
    }


def _tool(nome, **args):
    return {"type": "tool_use", "id": "x", "name": nome, "input": args}


def test_ferramentas_para_api_inclui_responder_e_type_object():
    f = L.ferramentas_para_api()
    assert [x["name"] for x in f][:-1] == [s["name"] for s in ESPECIFICACOES]
    assert f[-1]["name"] == "responder"
    assert all(x["input_schema"]["type"] == "object" for x in f)
    assert ESPECIFICACOES[0]["input_schema"].get("type") is None  # original intacto


def test_mensagens_reconstroi_o_historico():
    p = PlanejadorClaude("m", cliente=lambda c: _resp())
    h = [
        {"ferramenta": "margem_conciliar", "args": {}, "resultado": {"ok": True, "aprovado": True}}
    ]
    m = p._mensagens("oi", h)
    assert m[0] == {"role": "user", "content": "oi"}
    assert m[1]["content"][0]["type"] == "tool_use" and m[1]["content"][0]["id"] == "toolu_00"
    assert m[2]["content"][0]["tool_use_id"] == "toolu_00"
    assert json.loads(m[2]["content"][0]["content"])["aprovado"] is True


def test_proximo_ferramenta_e_resposta_e_contabiliza_uso():
    vistos = []

    def cli_falso(corpo):
        vistos.append(corpo)
        return _resp(_tool("margem_conciliar"))

    p = PlanejadorClaude("modelo-x", cli_falso, temperatura=0.0)
    passo = p.proximo("concilia?", [])
    assert passo.ferramenta == "margem_conciliar" and passo.args == {}
    assert vistos[0]["model"] == "modelo-x" and vistos[0]["temperature"] == 0.0
    assert vistos[0]["tool_choice"] == {"type": "any"}
    assert (p.uso.chamadas, p.uso.tokens_entrada, p.uso.tokens_saida) == (1, 10, 5)

    p2 = PlanejadorClaude(
        "m",
        lambda c: _resp(_tool("responder", status="ok", texto="t", dados={"a": 1})),
    )
    r = p2.proximo("q", []).resposta
    assert (r.status, r.texto, r.dados) == ("ok", "t", {"a": 1})
    sem_temp = []
    PlanejadorClaude(
        "m", lambda c: (sem_temp.append(c), _resp(_tool("margem_conciliar")))[1]
    ).proximo("q", [])
    assert "temperature" not in sem_temp[0]  # omitida por padrão (alguns modelos a rejeitam)


def test_para_passo_casos_de_borda():
    assert L._para_passo(_resp({"type": "text", "text": "oi"})).resposta.status == "erro"
    assert (
        L._para_passo(_resp(_tool("responder", status="talvez", texto="x"))).resposta.status
        == "erro"
    )
    r = L._para_passo(
        _resp(_tool("responder", status="recusa", texto="não", dados="lixo"))
    ).resposta
    assert r.status == "recusa" and r.dados == {}
    assert L._para_passo({"content": [{"type": "tool_use", "name": "margem_conciliar"}]}).args == {}


def test_cliente_http_sem_chave(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY ausente"):
        L.cliente_http()


class _Resp:
    def __init__(self, corpo):
        self.corpo = corpo

    def read(self):
        return json.dumps(self.corpo).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_cliente_http_envia_cabecalhos_e_repete_em_429(monkeypatch):
    chamadas = []

    def falso(req, timeout):
        chamadas.append(req)
        if len(chamadas) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "limite", {}, None)
        return _Resp({"content": [], "usage": {}})

    monkeypatch.setattr(L.urllib.request, "urlopen", falso)
    monkeypatch.setattr(L.time, "sleep", lambda s: None)
    c = L.cliente_http("chave-secreta", tentativas=3)
    assert c({"model": "m"}) == {"content": [], "usage": {}}
    assert len(chamadas) == 2
    assert chamadas[0].get_header("X-api-key") == "chave-secreta"
    assert chamadas[0].get_header("Anthropic-version") == L.VERSAO_API


def test_cliente_http_erro_nao_vaza_a_chave(monkeypatch):
    def falso(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "x-api-key chave-secreta", {}, None)

    monkeypatch.setattr(L.urllib.request, "urlopen", falso)
    with pytest.raises(RuntimeError) as e:
        L.cliente_http("chave-secreta")({})
    assert "chave-secreta" not in str(e.value) and "401" in str(e.value)


def _cliente_oraculo():
    """Cliente falso que 'é' o PlanejadorRegras atrás da API: prova o encanamento ponta a ponta."""
    regras = PlanejadorRegras()

    def chamar(corpo):
        msgs = corpo["messages"]
        pergunta = msgs[0]["content"]
        historico = []
        for a, u in zip(msgs[1::2], msgs[2::2], strict=False):
            uso = a["content"][0]
            historico.append(
                {
                    "ferramenta": uso["name"],
                    "args": uso["input"],
                    "resultado": json.loads(u["content"][0]["content"]),
                }
            )
        passo = regras.proximo(pergunta, historico)
        if passo.ferramenta:
            return _resp(_tool(passo.ferramenta, **passo.args))
        r = passo.resposta
        return _resp(_tool("responder", status=r.status, texto=r.texto, dados=r.dados))

    return chamar


def test_rodar_llm_ponta_a_ponta_com_cliente_falso(tmp_path):
    r = rodar_llm("modelo/falso:1", 2, "dev", tmp_path, cliente=_cliente_oraculo())
    assert r["conjuntos"]["dev"]["metricas"]["pass^k"][2] == 1.0
    assert r["conjuntos"]["dev"]["estado_alterado"] == 0
    assert r["uso"]["chamadas_api"] > 0 and r["uso"]["tokens_entrada"] > 0
    pasta = tmp_path / "llm" / "modelo_falso_1"
    assert (pasta / "resultados.json").exists() and (pasta / "transcripts.jsonl").exists()
    texto = (pasta / "RELATORIO.md").read_text(encoding="utf-8")
    assert "modelo/falso:1" in texto and "Nenhuma falha" in texto and "pass^2" in texto


def test_rodar_llm_heldout_registra_falhas(tmp_path):
    r = rodar_llm("m", 1, "heldout", tmp_path, cliente=_cliente_oraculo())
    assert r["conjuntos"]["heldout"]["falhas"]  # o stand-in falha no held-out, como esperado
    assert "(heldout)" in renderizar(r)


def test_cli_llm_modelo_exige_chave(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        cli.main(["--llm-modelo", "m", "--trials", "1", "--saida", str(tmp_path)])


def test_cli_llm_modelo_roda_e_imprime_uso(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("margem_real.agent.evals.llm_run.cliente_http", _cliente_oraculo)
    cli.main(["--llm-modelo", "m", "--trials", "1", "--split", "heldout", "--saida", str(tmp_path)])
    assert '"chamadas_api"' in capsys.readouterr().out
    assert not (tmp_path / "resultados.json").exists()  # o resultado determinístico não é tocado


# ---- formato "chat completions" (GitHub Models etc.) ----


def _resp_chat(nome=None, uso=(10, 5), **args):
    msg = {"role": "assistant", "content": "oi"}
    if nome:
        msg["tool_calls"] = [
            {
                "id": "c",
                "type": "function",
                "function": {"name": nome, "arguments": json.dumps(args)},
            }
        ]
    return {
        "choices": [{"message": msg}],
        "usage": {"prompt_tokens": uso[0], "completion_tokens": uso[1]},
    }


def test_ferramentas_chat_formato_function():
    f = C.ferramentas_chat()
    assert f[0]["type"] == "function" and f[0]["function"]["parameters"]["type"] == "object"
    assert f[-1]["function"]["name"] == "responder"


def test_chat_mensagens_e_passo():
    vistos = []
    p = PlanejadorChat("openai/x", lambda c: (vistos.append(c), _resp_chat("margem_conciliar"))[1])
    h = [{"ferramenta": "margem_conciliar", "args": {}, "resultado": {"ok": True}}]
    passo = p.proximo("oi", h)
    assert passo.ferramenta == "margem_conciliar"
    m = vistos[0]["messages"]
    assert m[0]["role"] == "system" and m[1] == {"role": "user", "content": "oi"}
    assert m[2]["tool_calls"][0]["id"] == "call_00" and m[3]["tool_call_id"] == "call_00"
    assert vistos[0]["tool_choice"] == "required" and "temperature" not in vistos[0]
    assert (p.uso.chamadas, p.uso.tokens_entrada, p.uso.tokens_saida) == (1, 10, 5)
    p2 = PlanejadorChat("m", lambda c: _resp_chat("margem_conciliar"), temperatura=0.0)
    p2.proximo("q", [])


def test_chat_para_passo_casos_de_borda():
    assert C._para_passo_chat({"choices": []}).resposta.status == "erro"
    assert C._para_passo_chat(_resp_chat()).resposta.status == "erro"
    ruim = {
        "choices": [{"message": {"tool_calls": [{"function": {"name": "x", "arguments": "{"}}]}}]
    }
    assert "JSON" in C._para_passo_chat(ruim).resposta.texto
    lista = {
        "choices": [{"message": {"tool_calls": [{"function": {"name": "x", "arguments": "[]"}}]}}]
    }
    assert C._para_passo_chat(lista).args == {}
    assert (
        C._para_passo_chat(_resp_chat("responder", status="talvez", texto="t")).resposta.status
        == "erro"
    )
    r = C._para_passo_chat(_resp_chat("responder", status="ok", texto="t", dados="lixo")).resposta
    assert r.status == "ok" and r.dados == {}
    r = C._para_passo_chat(_resp_chat("responder", status="ok", texto="t", dados={"a": 1})).resposta
    assert r.dados == {"a": 1}


def test_cliente_github_sem_token_e_cabecalhos(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN ausente"):
        C.cliente_github()
    chamadas = []

    def falso(req, timeout):
        chamadas.append(req)
        if len(chamadas) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "limite", {}, None)
        return _Resp({"choices": []})

    monkeypatch.setattr(C.urllib.request, "urlopen", falso)
    monkeypatch.setattr(C.time, "sleep", lambda s: None)
    c = C.cliente_github("tok-secreto")
    assert c({}) == {"choices": []} and len(chamadas) == 2
    assert chamadas[0].get_header("Authorization") == "Bearer tok-secreto"
    assert chamadas[0].full_url == C.URL_GITHUB


def test_cliente_chat_erro_nao_vaza_token(monkeypatch):
    def falso(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Bearer tok-secreto", {}, None)

    monkeypatch.setattr(C.urllib.request, "urlopen", falso)
    with pytest.raises(RuntimeError) as e:
        C.cliente_chat_http("https://x", "tok-secreto")({})
    assert "tok-secreto" not in str(e.value) and "401" in str(e.value)


def _cliente_oraculo_chat():
    regras = PlanejadorRegras()

    def chamar(corpo):
        msgs = corpo["messages"]
        historico = []
        for a, u in zip(msgs[2::2], msgs[3::2], strict=False):
            fn = a["tool_calls"][0]["function"]
            historico.append(
                {
                    "ferramenta": fn["name"],
                    "args": json.loads(fn["arguments"]),
                    "resultado": json.loads(u["content"]),
                }
            )
        passo = regras.proximo(msgs[1]["content"], historico)
        if passo.ferramenta:
            return _resp_chat(passo.ferramenta, **passo.args)
        r = passo.resposta
        return _resp_chat("responder", status=r.status, texto=r.texto, dados=r.dados)

    return chamar


def test_rodar_llm_provedor_github_ponta_a_ponta(tmp_path):
    r = rodar_llm(
        "openai/falso", 2, "dev", tmp_path, cliente=_cliente_oraculo_chat(), provedor="github"
    )
    assert r["provedor"] == "github" and r["conjuntos"]["dev"]["metricas"]["pass^k"][2] == 1.0
    assert "via github" in (tmp_path / "llm" / "openai_falso" / "RELATORIO.md").read_text(
        encoding="utf-8"
    )


def test_rodar_llm_provedor_invalido(tmp_path):
    with pytest.raises(ValueError, match="provedor desconhecido"):
        rodar_llm("m", 1, "dev", tmp_path, provedor="x")


def test_cli_provedor_github_exige_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        cli.main(
            ["--llm-modelo", "m", "--provedor", "github", "--trials", "1", "--saida", str(tmp_path)]
        )
