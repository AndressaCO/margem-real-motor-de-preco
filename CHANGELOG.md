# Changelog

Formato inspirado em Keep a Changelog. Datas no formato dd/mm/aaaa.

## 0.3.0 — 13/10/2026

### Adicionado
- `margem_real.agent.llm`: `PlanejadorClaude` (API Messages da Anthropic, sem dependência nova), ferramenta `responder` para encerrar com status e dados, contagem de tokens e tempo.
- `python -m margem_real.agent.evals --llm-modelo <id> [--trials N] [--split dev|heldout|todos]`: roda o harness com um LLM real e grava em `evals/llm/<modelo>/`.
- `PlanejadorChat` e `--provedor gemini`: avaliação no plano gratuito do Gemini (secret `GEMINI_API_KEY`). O GitHub Models foi tentado e não responde mais.
- Workflow `avaliar-llm` (somente `workflow_dispatch`, secret `ANTHROPIC_API_KEY`).
- 19 testes com cliente falso (total: 141 testes, 99% de cobertura).

### Conhecido
- Nenhuma execução contra um modelo real foi feita (sem chave no ambiente de desenvolvimento).

## 0.2.0 — 13/10/2026

### Adicionado
- `margem_real.tributos`: alíquota efetiva do Simples Nacional, Anexo I (LC 123/2006, redação LC 155/2016), com `Fraction`.
- `channels.com_simples()` e `--rbt12` na CLI para usar a alíquota efetiva única.
- `margem_real.pipeline`: contratos de schema, quarentena por linha, carga idempotente (hash do lote), upsert transacional, bloqueio por rejeição > 5% ou queda de volume > 50%, linhagem (`lote_id`), conciliação e SLA de frescor, logs JSON.
- `margem_real.agent`: 6 ferramentas somente leitura, planejador plugável, harness de avaliação (pass@k, pass^k, held-out, graders por estado final).
- Documentação: arquitetura, 3 ADRs, matriz de controles, datasheet, segurança, avaliação e benchmark.
- Infra: lock file, matriz de CI 3.11–3.13, Dependabot, gate de cobertura ≥ 95%, mypy, `scripts/auditar.py`, `scripts/atualizar_readme.py`.
- Testes de propriedade (Hypothesis). Total: 119 testes, 99% de cobertura.

### Alterado
- `requires-python >=3.11` e `pandas>=2.3` (piso real testado; 2.0.3 não instala).
- README reescrito; bloco de avaliação agora é gerado de `evals/resultados.json`.

### Corrigido
- `VERIFICACAO.md`: alíquotas do Simples a R$ 4,8 mi (11,125%) e R$ 3,6 mi (11,875%) estavam arredondadas errado.
- `pass@1` retornava `0.19999999999999996` (ponto flutuante).
- Relatório de avaliação quebrava com `--trials` diferente de 5.
- Logger duplicava handlers ao reconfigurar.
- Ordem do relatório não era determinística: `ORDER BY margem_contribuicao` empatava (valor arredondado a 2 casas) e a ordem dos empates variava com o número de threads do DuckDB. Achado pelo job de reprodutibilidade do CI (runner diferente da máquina local). Agora `ORDER BY margem_contribuicao, sku, canal`; 3 linhas do CSV de referência mudaram de posição (valores iguais) e há teste de regressão com 1, 2 e 8 threads.

### Conhecido
- Held-out do planejador de regras: 36,4%, incluindo uma resposta silenciosamente errada (h2). Mantido de propósito; ver `docs/AVALIACAO.md`.

## 0.1.0 — 13/10/2026

- Motor de preço mínimo/sugerido (Decimal), dados sintéticos, modelo SQL (DuckDB), relatório e 26 testes.
