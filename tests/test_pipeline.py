from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from margem_real.analysis import margem_por_sku_canal
from margem_real.channels import canais_dataframe
from margem_real.pipeline import (
    Armazem,
    ContratoViolado,
    QualidadeError,
    conciliar,
    frescor,
    validar_vendas,
)

SKUS = {"A", "B"}
CANAIS = {"c1", "c2"}


def _v(**o):
    base = dict(sku="A", canal="c1", mes="2026-01", unidades=3, preco=10.0)
    return {**base, **o}


def _df(*linhas):
    return pd.DataFrame(list(linhas))


def _novo_mes(vendas, n, mes):
    """n linhas de chaves distintas, todas num mês novo (nenhuma colide com o que existe)."""
    return vendas.drop_duplicates(["sku", "canal"]).iloc[:n].assign(mes=mes)


# ---- contrato ----------------------------------------------------------------
def test_coluna_ausente_viola_contrato():
    with pytest.raises(ContratoViolado, match="colunas ausentes"):
        validar_vendas(pd.DataFrame({"sku": ["A"]}), SKUS, CANAIS)


def test_tipo_incompativel_viola_contrato():
    with pytest.raises(ContratoViolado, match="numérico"):
        validar_vendas(_df(_v(preco="abc")), SKUS, CANAIS)


@pytest.mark.parametrize(
    "campo,valor,motivo",
    [
        ("sku", "Z", "sku_inexistente"),
        ("canal", "zz", "canal_inexistente"),
        ("mes", "2026-13", "mes_invalido"),
        ("mes", "26-01", "mes_invalido"),
        ("unidades", 0, "unidades_invalidas"),
        ("unidades", 2.5, "unidades_invalidas"),
        ("preco", 0.0, "preco_invalido"),
        ("preco", -3.0, "preco_invalido"),
        ("preco", float("inf"), "preco_invalido"),
        ("preco", float("nan"), "preco_invalido"),
    ],
)
def test_linha_invalida_vai_para_quarentena_com_motivo(campo, valor, motivo):
    r = validar_vendas(_df(_v(), {**_v(mes="2026-02"), campo: valor}), SKUS, CANAIS)
    assert len(r.validas) == 1
    assert motivo in r.rejeitadas["motivo"].iloc[0]


def test_linha_pode_acumular_motivos():
    r = validar_vendas(_df(_v(sku="Z", preco=-1.0)), SKUS, CANAIS)
    assert set(r.rejeitadas["motivo"].iloc[0].split(";")) == {"sku_inexistente", "preco_invalido"}


def test_duplicata_no_lote_mantem_a_ultima():
    r = validar_vendas(_df(_v(preco=10.0), _v(preco=12.0)), SKUS, CANAIS)
    assert r.validas["preco"].tolist() == [12.0]
    assert r.rejeitadas["motivo"].tolist() == ["chave_duplicada_no_lote"]


def test_lote_valido_nao_gera_rejeicao():
    r = validar_vendas(_df(_v(), _v(canal="c2")), SKUS, CANAIS)
    assert len(r.validas) == 2 and r.rejeitadas.empty and r.taxa_rejeicao == 0


# ---- armazém: idempotência, upsert, atomicidade --------------------------------
def test_reenvio_do_mesmo_lote_nao_altera_nada(armazem, dados):
    antes = armazem.impressao_digital()
    r = armazem.carregar_vendas(dados[1])
    assert r.status == "ignorado_idempotente"
    assert armazem.impressao_digital() == antes
    assert (
        armazem.con.execute("SELECT count(*) FROM execucoes WHERE tabela='vendas'").fetchone()[0]
        == 1
    )


def test_ordem_das_linhas_nao_muda_a_identidade_do_lote(armazem, dados):
    embaralhado = dados[1].sample(frac=1, random_state=1)
    assert armazem.carregar_vendas(embaralhado).status == "ignorado_idempotente"


def test_upsert_atualiza_e_conta_inseridas_e_atualizadas(armazem, dados):
    v = dados[1]
    n0 = armazem.con.execute("SELECT count(*) FROM vendas").fetchone()[0]
    novo = v.iloc[:5].copy()
    novo["preco"] = novo["preco"] + 1.0
    extra = pd.DataFrame([{**v.iloc[0].to_dict(), "mes": "2027-01"}])
    r = armazem.carregar_vendas(pd.concat([novo, extra]), queda_max_volume=0.999)
    assert (r.inseridas, r.atualizadas) == (1, 5)
    assert armazem.con.execute("SELECT count(*) FROM vendas").fetchone()[0] == n0 + 1
    p = armazem.con.execute(
        "SELECT preco FROM vendas WHERE sku=? AND canal=? AND mes=?",
        [novo.iloc[0]["sku"], novo.iloc[0]["canal"], novo.iloc[0]["mes"]],
    ).fetchone()[0]
    assert p == pytest.approx(novo.iloc[0]["preco"])


def test_invariante_entrada_igual_carregadas_mais_quarentena(armazem, dados):
    v = dados[1].iloc[:50].copy()
    v.loc[v.index[:2], "preco"] = -5.0
    r = armazem.carregar_vendas(v, queda_max_volume=0.99)
    assert r.linhas_entrada == r.linhas_carregadas + r.linhas_quarentena == 50
    assert r.linhas_quarentena == 2
    q = armazem.con.execute("SELECT motivo FROM quarentena").fetchall()
    assert [m[0] for m in q] == ["preco_invalido"] * 2


def test_lote_acima_do_limite_de_rejeicao_e_bloqueado_sem_carregar(armazem, dados):
    antes = armazem.impressao_digital()
    ruim = dados[1].copy()
    ruim.loc[ruim.index[: len(ruim) // 4], "preco"] = -1.0
    with pytest.raises(QualidadeError, match="rejeitadas"):
        armazem.carregar_vendas(ruim)
    assert armazem.impressao_digital() == antes  # atomicidade
    st = armazem.con.execute(
        "SELECT status FROM execucoes WHERE status <> 'ok' AND tabela='vendas'"
    ).fetchall()
    assert st == [("bloqueado_qualidade",)]  # a tentativa fica auditável
    assert armazem.con.execute("SELECT count(*) FROM quarentena").fetchone()[0] > 0


def test_baseline_de_volume_bloqueia_queda_brusca(armazem, dados):
    pouco = _novo_mes(dados[1], 10, "2030-01")
    with pytest.raises(QualidadeError, match="baseline"):
        armazem.carregar_vendas(pouco)


def test_lote_bloqueado_pode_ser_reenviado_corrigido(armazem, dados):
    v = _novo_mes(dados[1], 10, "2030-01")
    with pytest.raises(QualidadeError):
        armazem.carregar_vendas(v)
    ok = armazem.carregar_vendas(v, queda_max_volume=0.999)
    assert ok.status == "ok"  # bloqueio anterior não conta como execução aceita


def test_rollback_em_falha_inesperada_preserva_estado(armazem, dados, monkeypatch):
    antes = armazem.impressao_digital()

    def boom(*a, **k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(armazem, "_fechar_execucao", boom)
    novo = _novo_mes(dados[1], 30, "2031-01")
    with pytest.raises(RuntimeError):
        armazem.carregar_vendas(novo, queda_max_volume=0.999)
    assert armazem.impressao_digital() == antes


def test_linhagem_aponta_o_lote_de_origem(armazem, dados):
    lin = armazem.linhagem()
    assert lin["linhas_vivas"].sum() == len(dados[1])
    assert len(lin) == 1


def test_restricoes_do_banco_valem_mesmo_sem_a_validacao_em_python(armazem):
    with pytest.raises(Exception, match="(?i)constraint|check"):
        armazem.con.execute("INSERT INTO vendas VALUES ('x','y','2026-01', 1, -5, 'l')")


def test_persistencia_em_arquivo_e_idempotencia_entre_execucoes(tmp_path, dados):
    skus, vendas = dados
    caminho = tmp_path / "m.duckdb"
    a = Armazem(caminho)
    a.carregar_canais(canais_dataframe())
    a.carregar_skus(skus[["sku", "categoria", "custo"]])
    a.carregar_vendas(vendas)
    a.fechar()
    b = Armazem(caminho)  # novo processo, mesmo arquivo
    assert b.carregar_vendas(vendas).status == "ignorado_idempotente"
    assert b.carregar_skus(skus[["sku", "categoria", "custo"]]).status == "ignorado_idempotente"
    b.fechar()


# ---- controles ----------------------------------------------------------------
def test_conciliacao_fecha_receita_e_unidades(armazem):
    c = conciliar(armazem)
    assert c["aprovado"] and c["diferenca_unidades"] == 0
    assert c["diferenca_receita"] <= c["tolerancia"]


def test_conciliacao_detecta_divergencia(armazem, monkeypatch):
    import margem_real.pipeline.controls as ctl

    def mart_adulterado(v, s, c):
        m = margem_por_sku_canal(v, s, c)
        m.loc[m.index[0], "receita"] += 1000.0
        return m

    monkeypatch.setattr(ctl, "margem_por_sku_canal", mart_adulterado)
    assert conciliar(armazem)["aprovado"] is False


def test_frescor_respeita_o_sla(armazem):
    agora = datetime.now(UTC)
    assert frescor(armazem, 24, agora)["aprovado"]
    assert not frescor(armazem, 24, agora + timedelta(hours=30))["aprovado"]
    assert frescor(Armazem(), 24)["aprovado"] is False  # nunca carregou


def test_regressao_de_metrica_de_negocio_vs_pipeline_direto(armazem, dados):
    """O caminho pelo armazém tem que dar o MESMO número do caminho direto (sem pipeline)."""
    skus, vendas = dados
    direto = margem_por_sku_canal(vendas, skus, canais_dataframe())
    v, s, c = armazem.tabelas_para_analise()
    via = margem_por_sku_canal(v, s, c)
    assert via["margem_contribuicao"].sum() == pytest.approx(direto["margem_contribuicao"].sum())
    assert len(via) == len(direto)


# ---- CLIs e logs (fumaça) --------------------------------------------------------
def test_cli_pipeline_demonstra_idempotencia_e_bloqueio(tmp_path, capsys):
    import json

    from margem_real.pipeline.__main__ import main

    saida = tmp_path / "demo.json"
    main(["--skus", "30", "--semente", "3", "--json", str(saida)])
    d = json.loads(saida.read_text(encoding="utf-8"))
    assert d["carga_1"]["status"] == "ok"
    assert d["carga_2_mesmo_lote"]["status"] == "ignorado_idempotente"
    assert d["carga_3_corrompida"].startswith("bloqueada")
    assert d["conciliacao"]["aprovado"] is True


def test_logs_sao_json_e_configuracao_e_idempotente():
    import io
    import json

    from margem_real.pipeline import logs

    buf = io.StringIO()
    n0 = len(logs.LOGGER.handlers)
    logs.configurar(stream=buf)
    logs.configurar(stream=buf)  # segunda chamada não duplica handler
    assert len(logs.LOGGER.handlers) == max(n0, 1)  # sem duplicar
    logs.evento("teste_evento", lote_id="abc", n=3)
    linha = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert linha["evento"] == "teste_evento" and linha["lote_id"] == "abc" and linha["n"] == 3


def test_skus_invalidos_vao_para_quarentena_e_reenvio_e_idempotente():
    a = Armazem()
    skus = pd.DataFrame(
        {"sku": ["A", "B", "B", ""], "categoria": ["x"] * 4, "custo": [10.0, 5.0, 6.0, -1.0]}
    )
    r = a.carregar_skus(skus)
    assert (r.linhas_carregadas, r.linhas_quarentena) == (2, 2)
    motivos = {m for (m,) in a.con.execute("SELECT motivo FROM quarentena").fetchall()}
    assert {"sku_duplicado", "sku_vazio;custo_invalido"} <= motivos
    assert a.carregar_skus(skus).status == "ignorado_idempotente"


def test_rollback_em_carga_de_skus_com_falha(monkeypatch):
    a = Armazem()
    monkeypatch.setattr(
        a, "_fechar_execucao", lambda *x, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )
    with pytest.raises(RuntimeError):
        a.carregar_skus(pd.DataFrame({"sku": ["A"], "categoria": ["x"], "custo": [1.0]}))
    assert a.con.execute("SELECT count(*) FROM skus").fetchone()[0] == 0
