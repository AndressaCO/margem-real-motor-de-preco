# Benchmark e rodadas de auditoria

Este documento registra **contra o quê** o projeto foi comparado, **o que as fontes dizem** (com data de acesso) e **o que cada rodada de auditoria encontrou e corrigiu**.

**Limite declarado:** a auditoria é uma autoauditoria (eu escrevi o código, os critérios e o script que os checa), complementada por verificação automatizada em [`scripts/auditar.py`](../scripts/auditar.py), cujo resultado está em [`AUDITORIA.md`](../AUDITORIA.md). Não é revisão independente. Este material **não afirma** posição em percentil algum; não existe métrica que classifique portfólios assim.

## 1. Fontes consultadas (acessadas em 13/10/2026)

| Classe | Fonte | O que foi usado |
|---|---|---|
| PRÁTICA DE MERCADO | Google, *Engineering Practices*, "The Standard of Code Review" — <https://google.github.io/eng-practices/review/reviewer/standard.html> | Critério: a mudança deve melhorar a saúde do código mesmo sem ser perfeita; pequenas mudanças, revisão por critério explícito |
| PRÁTICA DE MERCADO | Anthropic Engineering, "Demystifying evals for AI agents" — <https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents> | Avaliar o **resultado** (estado final), não o caminho; ambiente limpo por trial; salvar transcrições; conjuntos com casos negativos; evitar saturação |
| PRÁTICA DE MERCADO | Anthropic Engineering, "Writing tools for agents" — <https://www.anthropic.com/engineering/writing-tools-for-agents> | Poucas ferramentas bem nomeadas (prefixo `margem_`), erros acionáveis, truncagem com `total`, esquema estrito |
| FATO (publicação revisada por pares/preprint) | Gebru et al., *Datasheets for Datasets*, arXiv:1803.09010 — <https://arxiv.org/abs/1803.09010> | Estrutura do `DATASHEET.md` |
| FATO | Chen et al., arXiv:2107.03374 (pass@k); Yao et al., arXiv:2406.12045 (τ-bench, pass^k) | Fórmulas implementadas com `Fraction` |
| FATO | COSO, *Internal Control — Integrated Framework* (2013): 5 componentes, 17 princípios (via resumo secundário, onspring.com) | Estrutura *inspirada* de `docs/CONTROLES.md` — não é implementação do COSO |
| FATO | LC 123/2006, Anexo I, redação LC 155/2016 — Planalto | Tabela do Simples em `tributos.py` |
| PRÁTICA DE MERCADO | Checklists de portfólio de engenharia de dados (datalakehousehub.com, 02/2026; dataengineeracademy.com, 28/01/2026) | Critérios: README primeiro, validações, testes, idempotência, observabilidade |
| Não confirmado | ACM *Artifact Review and Badging* | A página de revisores traz as definições "Reproduced"/"Replicated"; **não confirmei a versão da política**, portanto não reivindico selo algum |

## 2. Rubrica (20 critérios, executáveis)

Os critérios C01–C20 estão em `scripts/auditar.py` e agrupados em Qualidade, Reprodutibilidade, Documentação, Avaliação, Honestidade e Higiene. Cada um tem evidência impressa. Um critério só entra se for verificável por máquina; o que exige julgamento humano está em "Limites" (seção 5).

## 3. Rodadas

### Rodada 1 — cinco melhorias (todas aplicadas)

| # | Lacuna encontrada | Correção |
|---|---|---|
| 1 | Conjunto de avaliação sem generalização: 100% no dev esconde sobreajuste | 11 tarefas **held-out** escritas depois do planejador, sem ajuste a elas. Resultado: 36,4% — o número honesto |
| 2 | Só testes por exemplos | Testes de propriedade (Hypothesis): invariantes de preço, `pass@k`/`pass^k`, hash de lote. Um deles achou `0.19999999999999996` em `pass@1` → corrigido com `Fraction` |
| 3 | Reprodutibilidade frágil | Lock file (22 pacotes, Python 3.12.3), matriz de CI 3.11–3.13, Dependabot, gate de cobertura ≥ 95%, `pip-audit` sem vulnerabilidades conhecidas |
| 4 | Controladoria rasa para quem é controller | Módulo `tributos.py` (Simples Anexo I) e matriz de controles C1–C9 com limites declarados |
| 5 | Documentação insuficiente | `ARQUITETURA.md`, 3 ADRs, `DATASHEET.md`, `SECURITY.md`, `CONTROLES.md` |

### Rodada 2 — cinco melhorias (auditoria por script)

| # | Lacuna encontrada | Correção |
|---|---|---|
| 6 | Afirmações do README dependiam de eu lembrar de atualizá-las ("26 testes" já estava velho) | Bloco de avaliação gerado de `evals/resultados.json` (`scripts/atualizar_readme.py --check` no CI) |
| 7 | Erro numérico na minha própria verificação: Simples a R$ 4,8 mi escrito como 11,12% e a R$ 3,6 mi como 11,87% | Valores exatos são 11,125% e 11,875%; `VERIFICACAO.md` corrigido e checado por C17 |
| 8 | Bug de portabilidade só visto em ambiente limpo: relatório quebrava com `--trials 2` | `ks` derivados dos dados; teste dedicado |
| 9 | Piso de versões não era real: `pandas 2.0.3` não instalou, o teste de "piso" rodou em 2.3.3 | `requires-python >=3.11`, `pandas>=2.3`; só reivindico o que testei |
| 10 | Tipagem solta (8 erros do mypy após subir o alvo para 3.11) | Itertuples → `to_dict("records")` com `float()` explícito; mypy limpo em 25 arquivos |

### Rodada 3 — o CI independente achou um defeito que a máquina local não mostrava

| # | Lacuna encontrada | Correção |
|---|---|---|
| 11 | Mesmo com as versões fixadas (pandas 3.0.6, numpy 2.5.4, duckdb 1.5.6), o relatório do CI divergiu do versionado: só a **ordem** de linhas empatadas no `ORDER BY` mudou, porque o DuckDB paraleliza e o runner tem outro número de núcleos | `ORDER BY margem_contribuicao, sku, canal` (também no pandas); teste de regressão com 1, 2 e 8 threads (falha no SQL antigo, passa no novo); job de reprodutibilidade passa a usar o lock file e anotar a divergência |

Lição registrada: "reproduz na minha máquina" não era evidência suficiente; só o runner limpo expôs o defeito.

### Verificação final

Executada ao fechar esta versão; ver [`AUDITORIA.md`](../AUDITORIA.md) e o status do CI no GitHub. Se algum critério falhar ali, a versão não é publicada como "concluída".

## 4. Lacunas conhecidas (não corrigidas, de propósito)

| Lacuna | Por que não foi fechada |
|---|---|
| Nenhum LLM real avaliado | Planejador (`PlanejadorClaude`) e workflow `avaliar-llm` implementados e testados com cliente falso; falta executar com a chave (custo) |
| Held-out em 36,4% | É um resultado, não um defeito escondido; melhorar o planejador de regras seria ajustar ao held-out e invalidá-lo |
| Python 3.10 e pandas < 2.3 não suportados | Não testei; declarar suporte seria afirmar sem evidência |
| Windows/macOS | Não testados |
| Interpretação do ICMS na 6ª faixa | HIPÓTESE; exige contador |
| Revisão independente | Nenhuma foi feita |

## 5. Limites desta rubrica

1. Eu defini os critérios; um revisor externo pode ter outros.
2. As fontes de "o que recrutadores valorizam" são qualitativas e, em parte, blogs; não há estudo que ligue portfólio a taxa de entrevistas (HIPÓTESE, sem teste).
3. Verifiquei **presença e coerência**; não medi a qualidade do código por leitura de terceiros.
