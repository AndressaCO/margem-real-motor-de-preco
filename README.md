# Margem Real: preço mínimo e margem por SKU e canal

[![ci](https://github.com/AndressaCO/margem-real-motor-de-preco/actions/workflows/ci.yml/badge.svg)](https://github.com/AndressaCO/margem-real-motor-de-preco/actions/workflows/ci.yml)

> **Dados 100% sintéticos.** Alíquotas, comissões e fretes são ilustrativos e não representam nenhuma empresa nem tabela de marketplace. Troque pelos seus números e valide com seu contador.

**English summary:** SQL (DuckDB) + Python engine that computes contribution margin and a break-even ("minimum") price per SKU × sales channel, then simulates repricing to a target margin. It shows how one flat markup across channels can hide loss-making SKU/channel pairs. Synthetic data, tested (26 tests), reproducible.

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

## Como rodar

```bash
pip install -e ".[dev]"
python -m margem_real --skus 200 --markup 1.8 --margem-alvo 0.10 --semente 42
pytest && ruff check .
```

## Estrutura

```
src/margem_real/
  pricing.py      # preço mínimo, sugerido, margem (Decimal, validação de entradas)
  channels.py     # parâmetros ILUSTRATIVOS de canal
  synthetic.py    # gerador de dados reprodutível (semente)
  sql/margem_contribuicao.sql   # modelo analítico em DuckDB
  analysis.py     # SQL + resumo por canal + simulação de repricing
  cli.py          # gera relatório em Markdown e CSV
tests/            # 26 testes: contas manuais, invariantes, SQL × Python
```

## O que este projeto demonstra (e o que não)

| Área | Demonstrado aqui | Não demonstrado aqui |
|---|---|---|
| Controladoria e precificação | Margem de contribuição, preço mínimo e sugerido, markup × margem por canal, premissas e limites explícitos | Matriz de controles internos, conciliações, calendário fiscal, regime tributário detalhado |
| Engenharia de dados | Modelo analítico em SQL (DuckDB), geração reprodutível de dados, pacote Python, testes, lint e CI | Orquestração, cargas incrementais, qualidade de dados em escala, nuvem, dbt |
| Agentes de IA | Nada | Todo o tema |

## Decisões de projeto

- **Decimal, não float**, nas contas de preço: evita ruído binário e controla o arredondamento.
- **Duas implementações independentes** (SQL e Python) e testes que exigem que concordem.
- **Entradas validadas**: passar `34` em vez de `0.34` levanta erro, em vez de gerar preço absurdo.
- **Sem elasticidade**: o preço sugerido é o que a conta exige, não previsão de receita. Subir preço pode reduzir volume.

## Limites

Custos fixos da operação (folha, aluguel) ficam fora da margem de contribuição. Os parâmetros por canal são iguais para todos os SKUs do canal. Não há ST, DIFAL nem regime tributário detalhado: o imposto entra como alíquota única por canal. No Simples Nacional real a alíquota efetiva é a mesma em todos os canais; aqui ela varia por canal só para fins didáticos (ver `VERIFICACAO.md`).

Veja [`VERIFICACAO.md`](VERIFICACAO.md) para o que foi e o que não foi verificado.

## Licença

MIT. Autora: Andressa Cunha de Oliveira.
