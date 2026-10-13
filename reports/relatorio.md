# Relatório de margem por SKU e canal

> Dados 100% sintéticos e parâmetros de canal ilustrativos. Valide alíquotas e regime com seu contador.

Parâmetros: 200 SKUs, markup fixo de 1,8 em todos os canais,
margem alvo de 10,0%, semente 42.

## Visão geral

- Receita total simulada: R$ 1.671.731,82
- Margem de contribuição total: R$ 182.257,81 (10,9%)
- Pares SKU x canal vendendo abaixo do preço mínimo: 95 de 667
  (14,2%), somando 7,8% da receita

## Por canal

| canal | pares | receita | margem_contribuicao | margem_pct | pct_pares_no_prejuizo |
|---|---|---|---|---|---|
| marketplace_a | 157 | R$ 545.972,72 | R$ 9.892,87 | 1,8% | 60,5% |
| marketplace_b | 173 | R$ 493.596,21 | R$ 33.230,02 | 6,7% | 0,0% |
| site_proprio | 167 | R$ 289.503,50 | R$ 41.467,69 | 14,3% | 0,0% |
| b2b_distribuicao | 170 | R$ 342.659,39 | R$ 97.667,23 | 28,5% | 0,0% |

## Oito piores pares e o preço que a conta exige

| sku | canal | preco_medio_praticado | preco_minimo | preco_sugerido | variacao_pct |
|---|---|---|---|---|---|
| SKU-0146 | marketplace_a | R$ 44,71 | R$ 48,72 | R$ 57,75 | 29,2% |
| SKU-0061 | marketplace_a | R$ 14,07 | R$ 21,96 | R$ 26,02 | 84,9% |
| SKU-0189 | marketplace_a | R$ 19,22 | R$ 26,07 | R$ 30,89 | 60,7% |
| SKU-0093 | marketplace_a | R$ 45,00 | R$ 48,44 | R$ 57,41 | 27,6% |
| SKU-0152 | marketplace_a | R$ 25,64 | R$ 31,90 | R$ 37,80 | 47,4% |
| SKU-0032 | marketplace_a | R$ 45,14 | R$ 49,05 | R$ 58,13 | 28,8% |
| SKU-0160 | marketplace_a | R$ 21,58 | R$ 29,07 | R$ 34,45 | 59,6% |
| SKU-0095 | marketplace_a | R$ 14,26 | R$ 21,91 | R$ 25,97 | 82,1% |

## Hipóteses e limites

- O preço sugerido não modela elasticidade: subir preço pode reduzir volume.
- Os custos de canal são ilustrativos e iguais para todos os SKUs de um canal.
- Custos fixos da operação (folha, aluguel) ficam fora da margem de contribuição.
