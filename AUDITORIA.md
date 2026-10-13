# Auditoria automatizada

Gerada por `scripts/auditar.py` em 13/10/2026 21:18 UTC. Modo: completo.

Resultado: 20 OK, 0 falhas, 0 puladas de 20.

**Limite:** é autoauditoria automatizada sobre critérios que eu mesma defini (ver `docs/BENCHMARK.md`). Não é revisão independente nem certificação.

| ID | Grupo | Critério | Status | Evidência |
|---|---|---|---|---|
| C01 | Qualidade | Lint e formatação (ruff) | OK | ruff check e format limpos |
| C02 | Qualidade | Tipagem estática (mypy) | OK | Success: no issues found in 28 source files |
| C03 | Qualidade | Testes + cobertura ≥ 95% | OK | 143 passed in 94.48s (0:01:34) | TOTAL                                      1210     13    99% |
| C04 | Reprodutibilidade | Relatório regenerado = versionado | OK | relatório e CSV idênticos aos versionados |
| C05 | Reprodutibilidade | CI com matriz 3.11–3.13 e gates | OK | matriz 3.11–3.13, mypy, gate de cobertura e auditoria |
| C06 | Reprodutibilidade | Lock file de dependências | OK | 22 dependências fixadas |
| C07 | Documentação | Docs obrigatórios presentes | OK | ok |
| C08 | Documentação | ≥ 3 ADRs | OK | 3 ADRs |
| C09 | Documentação | Datasheet com seções de Gebru | OK | seções de Gebru presentes |
| C10 | Avaliação | ≥ 30 tarefas dev e ≥ 10 held-out | OK | dev=31, held-out=11 |
| C11 | Avaliação | Casos negativos/limite presentes | OK | categorias de recusa/limite/esclarecimento/controle: 4 |
| C12 | Avaliação | Transcrições versionadas | OK | 2 arquivos de transcrição |
| C13 | Honestidade | README = resultados.json | OK | bloco do README em dia com resultados.json |
| C14 | Honestidade | Stand-in e held-out expostos no README | OK | planejador declarado como stand-in e held-out exposto |
| C15 | Honestidade | Sem afirmação de percentil sem ressalva | OK | nenhuma afirmação de percentil sem ressalva |
| C16 | Honestidade | VERIFICACAO separa FATO/PRÁTICA/HIPÓTESE | OK | classes FATO/PRÁTICA/HIPÓTESE e lista de não verificados |
| C17 | Honestidade | Valores do Simples corrigidos | OK | Simples: 11,125% e 11,875% (valores antigos só na nota de correção) |
| C18 | Higiene | Links relativos resolvem | OK | links relativos resolvem |
| C19 | Higiene | Sem segredos | OK | nenhum padrão de segredo |
| C20 | Higiene | Sem referência a empregador/cliente real | OK | sem referência a empregador/cliente real |
