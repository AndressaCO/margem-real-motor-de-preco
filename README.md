# Margem Real: preço mínimo e margem por SKU e canal

[![ci](https://github.com/AndressaCO/margem-real-motor-de-preco/actions/workflows/ci.yml/badge.svg)](https://github.com/AndressaCO/margem-real-motor-de-preco/actions/workflows/ci.yml)

> **Dados 100% sintéticos.** Alíquotas, comissões e fretes são ilustrativos e não representam nenhuma empresa nem tabela de marketplace. Troque pelos seus números e valide com seu contador.

**English summary:** a small, fully reproducible stack in three layers. (1) **Controllership**: contribution margin, break-even price and Simples Nacional effective rate per SKU × channel. (2) **Data engineering**: a contract-checked, idempotent load pipeline (DuckDB) with quarantine, lineage, reconciliation and freshness controls. (3) **AI-agent evaluation**: a read-only tool layer plus an eval harness (pass@k / pass^k, held-out split, state-based graders). The agent's planner is a rule-based **stand-in, not a language model**; the evals are there to show how one would be tested. Synthetic data, 144 tests, 99% coverage, CI on Python 3.11–3.13. LLM planners are implemented and unit-tested with a fake client; **one** real run exists (Gemini, held-out, 11/11, single trial, see `docs/RESULTADO-LLM-GEMINI.md`), too small and possibly contaminated to be called a benchmark.

## Três camadas, um problema

| Camada | O que faz | Onde está |
|---|---|---|
| Controladoria | Preço mínimo/sugerido, margem por SKU × canal, alíquota efetiva do Simples (Anexo I), matriz de controles C1–C9 | `pricing.py`, `tributos.py`, [`docs/CONTROLES.md`](docs/CONTROLES.md) |
| Engenharia de dados | Contrato de schema, quarentena por linha, carga idempotente (hash do lote), upsert transacional, bloqueio por taxa de rejeição/queda de volume, linhagem, conciliação, SLA de frescor | `pipeline/`, [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) |
| Agente de IA (avaliação) | 6 ferramentas somente leitura, planejador plugável, harness de avaliação com pass@k e pass^k, conjunto held-out | `agent/`, [`docs/AVALIACAO.md`](docs/AVALIACAO.md) |

Decisões registradas em [ADRs](docs/adr/). Metodologia e auditoria: [`docs/BENCHMARK.md`](docs/BENCHMARK.md) e [`AUDITORIA.md`](AUDITORIA.md).

## A pergunta de negócio

Um markup único (aqui, 1,8× o custo) dá a mesma margem em todos os canais? Não: cada canal cobra imposto, comissão, frete, devolução e mídia em proporções diferentes. Quais pares SKU × canal vendem abaixo do preço mínimo, e a que preço precisam ser vendidos para entregar 10% de margem?

## Resultado da simulação (semente 42, 200 SKUs, 6 meses)

| Indicador | Valor |
|---|---|
| Receita simulada | R$ 1.671.731,82 |
| Margem de contribuição | R$ 182.257,81 (10,9%) |
| Pares SKU × canal abaixo do preço mínimo | 95 de 667 (14,2%), 7,8% da receita |
| Pior canal (`marketplace_a`) | margem de 1,8%, com 60,5% dos pares no prejuízo |
| Melhor canal (`b2b_distribuicao`) | margem de 28,5% |

**Leitura honesta:** o resultado decorre dos parâmetros ilustrativos que defini; ele demonstra o método, não um fato de mercado. O valor do projeto é a conta aberta e reproduzível, que qualquer empresa pode repetir com seus próprios números.

Relatório completo: [`reports/relatorio.md`](reports/relatorio.md) · Dados por par: [`reports/margem_por_sku_canal.csv`](reports/margem_por_sku_canal.csv)

## A conta

Despesas proporcionais ao preço (imposto + comissão + frete + devolução + mídia) somam `d`; a taxa fixa por unidade é `f`; o custo é `c`; a margem alvo é `m`.

```
preço mínimo   = (c + f) / (1 - d)          # margem de contribuição = 0
preço sugerido = (c + f) / (1 - d - m)      # margem líquida = m
margem líquida = (preço - c - f - preço·d) / preço
```

Exemplo: `c = 100`, `d = 34%`, `f = 0` → mínimo `100 / 0,66 = R$ 151,52` e sugerido (10%) `100 / 0,56 = R$ 178,58`. Preços arredondam **para cima** ao centavo, para nunca ficar abaixo do ponto de equilíbrio.

## Como rodar (quickstart)

```bash
pip install -e ".[dev]"                      # Python 3.11+. Versões fixadas (3.12+): pip install -r requirements-dev.lock && pip install -e . --no-deps
python -m margem_real --skus 200 --markup 1.8 --margem-alvo 0.10 --semente 42
python -m margem_real --rbt12 1000000        # mesmo relatório com a alíquota efetiva do Simples (8,45%)
python -m margem_real.pipeline --skus 100    # demonstração da carga com controles
python -m margem_real.agent.evals --trials 5 # reavalia o agente e regrava evals/
make check                                   # ruff + mypy + pytest (cobertura >= 95%) + auditoria
```

## Avaliação do agente (gerada de `evals/resultados.json`)

<!-- eval:begin -->
| Planejador | Conjunto | Tarefas | pass@1 | pass^1 | pass^5 |
|---|---|---|---|---|---|
| regras | dev | 31 | 100,0% | 100,0% | 100,0% |
| regras | heldout | 11 | 36,4% | 36,4% | 36,4% |
| ruidoso(p=0.25) | dev | 31 | 68,4% | 68,4% | 6,5% |
| ruidoso(p=0.25) | heldout | 11 | 25,5% | 25,5% | 0,0% |
<!-- eval:end -->

Como ler, sem exagero:

- O planejador `regras` **não é um modelo de linguagem**: é um stand-in determinístico (regex). Nenhum número acima mede um LLM.
- `dev` = tarefas usadas enquanto o planejador era escrito; 100% ali é esperado e **não prova generalização**. O conjunto **held-out** (36,4%) é o número honesto: ele expôs 6 falhas de roteamento e 1 resposta silenciosamente errada (o custo fixo era ignorado), que estão registradas, não escondidas.
- `ruidoso` injeta falhas com taxa conhecida só para provar que o harness as detecta (pass^5 cai a 6,5% no dev).
- Há planejadores de LLM prontos (`PlanejadorClaude`, API Messages da Anthropic, pago; `PlanejadorChat`, plano gratuito do Gemini) e um workflow manual (`avaliar-llm`) que os roda na nuvem do GitHub com o mesmo harness. **Testado com um cliente falso e executado uma vez contra um modelo real** (Gemini `gemini-3.5-flash-lite`, held-out, 11/11, 1 trial, 13/10/2026): resultado em `docs/RESULTADO-LLM-GEMINI.md`, com ressalvas (n pequeno, IC 95% ≈ 71,5–100%, prompt e tarefas do mesmo autor, transcrições não revisadas). Como rodar: `docs/AVALIACAO.md`.

## Estrutura

```
src/margem_real/
  pricing.py      # preço mínimo, sugerido, margem (Decimal, validação de entradas)
  tributos.py     # alíquota efetiva do Simples, Anexo I (Fractions, tabela da LC 123/2006)
  channels.py     # parâmetros ILUSTRATIVOS de canal; com_simples() uniformiza o imposto
  synthetic.py    # gerador de dados reprodutível (semente)
  analysis.py     # SQL + resumo por canal + simulação de repricing
  cli.py          # relatório em Markdown e CSV
  pipeline/       # contratos, armazém DuckDB, controles, logs JSON
  agent/          # ferramentas, planejadores, evals (tarefas, graders, métricas)
tests/            # 144 testes: contas manuais, propriedades (Hypothesis), pipeline, agente
docs/ evals/ scripts/ DATASHEET.md SECURITY.md CHANGELOG.md AUDITORIA.md
```

## O que este projeto demonstra (e o que não)

| Área | Demonstrado aqui | Não demonstrado aqui |
|---|---|---|
| Controladoria e precificação | Margem de contribuição, preço mínimo e sugerido, Simples Anexo I, matriz de controles (inspirada no COSO 2013), premissas e limites | ST, DIFAL, fator R, transição CBS/IBS, calendário fiscal, revisão por contador |
| Engenharia de dados | Contratos, quarentena, idempotência, upsert transacional, linhagem, conciliação, SLA de frescor, lock file, CI em matriz | Orquestrador (Airflow/Dagster), carga incremental em volume, nuvem, dbt, banco compartilhado |
| Agentes de IA | Camada de ferramentas somente leitura com erros acionáveis; harness com pass@k/pass^k, held-out, graders por estado final | Mais de uma execução de LLM e revisão manual das transcrições (há 1 execução, 11 tarefas), avaliação humana, red-teaming |

## Decisões de projeto

- **Decimal, não float**, nas contas de preço: evita ruído binário e controla o arredondamento.
- **Duas implementações independentes** (SQL e Python) e testes que exigem que concordem.
- **Entradas validadas**: passar `34` em vez de `0.34` levanta erro, em vez de gerar preço absurdo.
- **Sem elasticidade**: o preço sugerido é o que a conta exige, não previsão de receita. Subir preço pode reduzir volume.

## Limites

Custos fixos da operação (folha, aluguel) ficam fora da margem de contribuição. Os parâmetros por canal são iguais para todos os SKUs do canal. Não há ST, DIFAL nem regime tributário detalhado: o imposto entra como alíquota única por canal. No Simples Nacional real a alíquota efetiva é a mesma em todos os canais; aqui ela varia por canal só para fins didáticos (ver `VERIFICACAO.md`).

No Simples, a alíquota efetiva **cai** ao cruzar R$ 3,6 mi (11,875% → ~8,5%) porque a coluna de ICMS da 6ª faixa é "-"; a leitura de que o ICMS passa a ser recolhido fora do DAS é **hipótese** a confirmar com contador. Veja [`VERIFICACAO.md`](VERIFICACAO.md) para o que foi e o que não foi verificado, e [`CHANGELOG.md`](CHANGELOG.md) para o histórico.

## Licença

MIT. Autora: Andressa Cunha de Oliveira.
