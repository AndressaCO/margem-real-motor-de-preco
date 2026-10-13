"""Auditoria como código: verifica, de forma reproduzível, o que o README e os docs afirmam.

Uso:
    python scripts/auditar.py            # completa (ruff, mypy, pytest com cobertura, relatório)
    python scripts/auditar.py --rapido   # só verificações estáticas (sem rodar a suíte)

Escreve AUDITORIA.md e sai com código 1 se algum critério falhar.
Limite declarado: é uma autoauditoria automatizada. Não substitui revisão independente.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
Resultado = tuple[bool, str]


@dataclass
class Criterio:
    id: str
    grupo: str
    descricao: str
    fn: Callable[[], Resultado]
    lento: bool = False


def _ler(rel: str) -> str:
    p = RAIZ / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _sh(*cmd: str) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, check=False)
    return r.returncode, (r.stdout + r.stderr).strip()


def _existem(*caminhos: str) -> Resultado:
    faltam = [c for c in caminhos if not (RAIZ / c).exists()]
    return (not faltam, "ok" if not faltam else "faltam: " + ", ".join(faltam))


# ------------------------------------------------------------------ verificações


def c_ruff() -> Resultado:
    a, _ = _sh(sys.executable, "-m", "ruff", "check", ".")
    b, _ = _sh(sys.executable, "-m", "ruff", "format", "--check", ".")
    return (a == 0 and b == 0, "ruff check e format limpos" if a == b == 0 else "ruff falhou")


def c_mypy() -> Resultado:
    rc, out = _sh(sys.executable, "-m", "mypy")
    return rc == 0, out.splitlines()[-1] if out else ""


def c_pytest() -> Resultado:
    rc, out = _sh(sys.executable, "-m", "pytest", "-q", "--cov=margem_real", "--cov-fail-under=95")
    resumo = [x for x in out.splitlines() if " passed" in x or " failed" in x]
    total = [x for x in out.splitlines() if x.startswith("TOTAL")]
    return rc == 0, ((resumo[-1] if resumo else "") + " | " + (total[0] if total else "")).strip()


def c_relatorio() -> Resultado:
    tmp = RAIZ / ".auditoria_tmp"
    tmp.mkdir(exist_ok=True)
    rc, out = _sh(
        sys.executable,
        "-m",
        "margem_real",
        "--saida",
        str(tmp / "r.md"),
        "--csv",
        str(tmp / "r.csv"),
    )
    ok = rc == 0
    for nome, ref in (
        ("r.md", "reports/relatorio.md"),
        ("r.csv", "reports/margem_por_sku_canal.csv"),
    ):
        ok = ok and (tmp / nome).read_bytes() == (RAIZ / ref).read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return ok, "relatório e CSV idênticos aos versionados" if ok else (out or "divergência")


def c_ci() -> Resultado:
    t = _ler(".github/workflows/ci.yml")
    ok = all(x in t for x in ("3.11", "3.12", "3.13", "mypy", "cov-fail-under", "auditar.py"))
    return (
        ok,
        "matriz 3.11–3.13, mypy, gate de cobertura e auditoria" if ok else "ci.yml incompleto",
    )


def c_lock() -> Resultado:
    t = _ler("requirements-dev.lock")
    n = len([x for x in t.splitlines() if "==" in x])
    return n >= 10, f"{n} dependências fixadas"


def c_docs() -> Resultado:
    return _existem(
        "docs/ARQUITETURA.md",
        "docs/CONTROLES.md",
        "docs/BENCHMARK.md",
        "docs/AVALIACAO.md",
        "DATASHEET.md",
        "SECURITY.md",
        "CHANGELOG.md",
        "VERIFICACAO.md",
        ".github/dependabot.yml",
    )


def c_adrs() -> Resultado:
    n = len(list((RAIZ / "docs/adr").glob("0*.md")))
    return n >= 3, f"{n} ADRs"


def c_datasheet() -> Resultado:
    t = _ler("DATASHEET.md").lower()
    secoes = ("motivação", "composição", "coleta", "usos", "distribuição", "manutenção")
    falta = [s for s in secoes if s not in t]
    return not falta, "seções de Gebru presentes" if not falta else f"faltam: {falta}"


def _res() -> dict:
    return json.loads(_ler("evals/resultados.json") or "{}")


def c_tarefas() -> Resultado:
    r = _res()["planejadores"]["regras"]
    dev, ho = r["dev"]["tarefas"], r["heldout"]["tarefas"]
    return dev >= 30 and ho >= 10, f"dev={dev}, held-out={ho}"


def c_negativos() -> Resultado:
    cat = _res()["planejadores"]["regras"]["dev"]["por_categoria"]
    neg = sum(1 for k in cat if k in ("negativo", "limite", "esclarecimento", "controle"))
    return neg >= 3, f"categorias de recusa/limite/esclarecimento/controle: {neg}"


def c_transcripts() -> Resultado:
    arquivos = list((RAIZ / "evals/transcripts").glob("*.jsonl"))
    return len(arquivos) >= 2, f"{len(arquivos)} arquivos de transcrição"


def c_readme_eval() -> Resultado:
    """O bloco de eval do README deve refletir evals/resultados.json (sem números soltos)."""
    rc, out = _sh(sys.executable, "scripts/atualizar_readme.py", "--check")
    return rc == 0, "bloco do README em dia com resultados.json" if rc == 0 else out[-200:]


def c_readme_honesto() -> Resultado:
    t = _ler("README.md").lower()
    pedacos = ("não é um modelo", "held-out", "quickstart" if "quickstart" in t else "como rodar")
    falta = [p for p in pedacos if p not in t]
    return not falta, "planejador declarado como stand-in e held-out exposto" if not falta else str(
        falta
    )


def c_sem_superlativo() -> Resultado:
    achados = []
    for rel in ("README.md", "docs/BENCHMARK.md", "docs/AVALIACAO.md", "DATASHEET.md"):
        for i, linha in enumerate(_ler(rel).splitlines(), 1):
            baixa = linha.lower()
            if "top 0,01" in baixa and not any(
                n in baixa for n in ("não afirma", "não é", "sem", "nunca")
            ):
                achados.append(f"{rel}:{i}")
    return not achados, "nenhuma afirmação de percentil sem ressalva" if not achados else str(
        achados
    )


def c_verificacao() -> Resultado:
    t = _ler("VERIFICACAO.md")
    ok = all(x in t for x in ("FATO", "PRÁTICA DE MERCADO", "HIPÓTESE", "NÃO verificado"))
    return ok, "classes FATO/PRÁTICA/HIPÓTESE e lista de não verificados" if ok else "incompleto"


def c_verificacao_simples() -> Resultado:
    t = _ler("VERIFICACAO.md")
    velhos = [
        i
        for i, linha in enumerate(t.splitlines(), 1)
        if ("11,87%" in linha or "11,12%" in linha) and "arredondados errado" not in linha
    ]
    ok = "11,125%" in t and "11,875%" in t and not velhos
    return ok, "Simples: 11,125% e 11,875% (valores antigos só na nota de correção)" if ok else str(
        velhos
    )


def c_links() -> Resultado:
    quebrados = []
    for md in list(RAIZ.glob("*.md")) + list((RAIZ / "docs").rglob("*.md")):
        for alvo in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", md.read_text(encoding="utf-8")):
            if alvo.startswith(("http", "mailto:")):
                continue
            if not (md.parent / alvo).resolve().exists():
                quebrados.append(f"{md.relative_to(RAIZ)} -> {alvo}")
    return not quebrados, "links relativos resolvem" if not quebrados else "; ".join(quebrados)


def c_segredos() -> Resultado:
    padrao = re.compile(
        r"(ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,})"
    )
    achados = []
    for p in RAIZ.rglob("*"):
        if (
            p.is_file()
            and ".git" not in p.parts
            and p.suffix in {".py", ".md", ".yml", ".toml", ".json", ".sql", ".lock"}
        ):
            if padrao.search(p.read_text(encoding="utf-8", errors="ignore")):
                achados.append(str(p.relative_to(RAIZ)))
    return not achados, "nenhum padrão de segredo" if not achados else str(achados)


def c_sem_empresa() -> Resultado:
    achados = [
        str(p.relative_to(RAIZ))
        for p in RAIZ.rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".md", ".yml", ".sql", ".csv", ".json"}
        and ".git" not in p.parts
        and p.name != "auditar.py"
        and "rs performance" in p.read_text(encoding="utf-8", errors="ignore").lower()
    ]
    return not achados, "sem referência a empregador/cliente real" if not achados else str(achados)


CRITERIOS = [
    Criterio("C01", "Qualidade", "Lint e formatação (ruff)", c_ruff, True),
    Criterio("C02", "Qualidade", "Tipagem estática (mypy)", c_mypy, True),
    Criterio("C03", "Qualidade", "Testes + cobertura ≥ 95%", c_pytest, True),
    Criterio("C04", "Reprodutibilidade", "Relatório regenerado = versionado", c_relatorio, True),
    Criterio("C05", "Reprodutibilidade", "CI com matriz 3.11–3.13 e gates", c_ci),
    Criterio("C06", "Reprodutibilidade", "Lock file de dependências", c_lock),
    Criterio("C07", "Documentação", "Docs obrigatórios presentes", c_docs),
    Criterio("C08", "Documentação", "≥ 3 ADRs", c_adrs),
    Criterio("C09", "Documentação", "Datasheet com seções de Gebru", c_datasheet),
    Criterio("C10", "Avaliação", "≥ 30 tarefas dev e ≥ 10 held-out", c_tarefas),
    Criterio("C11", "Avaliação", "Casos negativos/limite presentes", c_negativos),
    Criterio("C12", "Avaliação", "Transcrições versionadas", c_transcripts),
    Criterio("C13", "Honestidade", "README = resultados.json", c_readme_eval),
    Criterio("C14", "Honestidade", "Stand-in e held-out expostos no README", c_readme_honesto),
    Criterio("C15", "Honestidade", "Sem afirmação de percentil sem ressalva", c_sem_superlativo),
    Criterio("C16", "Honestidade", "VERIFICACAO separa FATO/PRÁTICA/HIPÓTESE", c_verificacao),
    Criterio("C17", "Honestidade", "Valores do Simples corrigidos", c_verificacao_simples),
    Criterio("C18", "Higiene", "Links relativos resolvem", c_links),
    Criterio("C19", "Higiene", "Sem segredos", c_segredos),
    Criterio("C20", "Higiene", "Sem referência a empregador/cliente real", c_sem_empresa),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rapido", action="store_true", help="pula ruff, mypy, pytest e relatório")
    args = ap.parse_args()

    linhas, falhas, puladas = [], 0, 0
    for c in CRITERIOS:
        if args.rapido and c.lento:
            linhas.append(f"| {c.id} | {c.grupo} | {c.descricao} | PULADO | (modo rápido) |")
            puladas += 1
            continue
        try:
            ok, det = c.fn()
        except Exception as e:  # noqa: BLE001 - a auditoria não pode cair por um critério
            ok, det = False, f"erro: {e!r}"
        falhas += not ok
        linhas.append(
            f"| {c.id} | {c.grupo} | {c.descricao} | {'OK' if ok else 'FALHOU'} | {det} |"
        )

    agora = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    total = len(CRITERIOS)
    ok_n = total - falhas - puladas
    modo = "rápido" if args.rapido else "completo"
    cab = (
        "# Auditoria automatizada\n\n"
        f"Gerada por `scripts/auditar.py` em {agora}. Modo: {modo}.\n\n"
        f"Resultado: {ok_n} OK, {falhas} falhas, {puladas} puladas de {total}.\n\n"
        "**Limite:** é autoauditoria automatizada sobre critérios que eu mesma defini "
        "(ver `docs/BENCHMARK.md`). Não é revisão independente nem certificação.\n\n"
        "| ID | Grupo | Critério | Status | Evidência |\n|---|---|---|---|---|\n"
    )
    destino = RAIZ / ("AUDITORIA.md" if not args.rapido else ".auditoria_rapida.md")
    destino.write_text(cab + "\n".join(linhas) + "\n", encoding="utf-8")
    print(cab + "\n".join(linhas))
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
