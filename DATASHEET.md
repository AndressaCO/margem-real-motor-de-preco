# Datasheet — dados sintéticos do projeto

Estrutura baseada em *Datasheets for Datasets* (Gebru et al., arXiv:1803.09010, v8): motivação,
composição, coleta, pré-processamento, usos, distribuição, manutenção. Itens do artigo que não
se aplicam a dados sintéticos estão marcados como tal.

**Motivação.** Permitir demonstrar precificação, margem por canal, engenharia de dados e um
agente avaliável sem expor dado de nenhuma empresa. Criado por Andressa Cunha de Oliveira, sem
financiamento externo.

**Composição.** Três tabelas.
- `skus(sku, categoria, custo)`: código `SKU-0001…`, 6 categorias genéricas de autopeças, custo lognormal (média log 3,6; desvio 0,9), limitado a R$ 4–900.
- `canais(canal, pct_despesas, custo_fixo)`: 4 canais com parâmetros **ilustrativos** (ver `channels.py`).
- `vendas(sku, canal, mes, unidades, preco)`: 6 meses (2026-01 a 2026-06); unidades ~ Poisson com popularidade Pareto; preço = custo x markup 1,80, com 20% de chance de promoção de 3% a 10%; cada SKU aparece em ~85% dos canais.
Não há dado pessoal, identificador de pessoa, nem informação confidencial. Não há rótulos nem divisão treino/teste; a divisão dev/held-out vale só para as tarefas de avaliação do agente.

**Processo de coleta.** Geração por código (`synthetic.py`) com `numpy.random.default_rng(semente)`. Mesma semente, mesma saída (testado). Nenhuma coleta de dados reais.

**Pré-processamento.** Nenhum além do contrato e da quarentena do pipeline (`pipeline/contracts.py`).

**Usos pretendidos.** Demonstração, ensino, testes de software e de avaliação de agentes. **Usos não recomendados:** estimar margem, preço ou carga tributária de qualquer empresa real; benchmark de modelos preditivos (a distribuição foi escolhida por conveniência, não ajustada a dados reais).

**Limites conhecidos.** Política de preço única (markup fixo) por construção; sem sazonalidade, sem elasticidade, sem devoluções reais; parâmetros de canal não vêm de tabela de marketplace; distribuições não foram validadas contra nenhum catálogo real.

**Distribuição.** Código e dados gerados sob licença MIT, neste repositório.

**Manutenção.** Mantido por Andressa Cunha de Oliveira (GitHub: AndressaCO). Mudanças nas distribuições alteram os números do README e de `reports/`; o CI regera e compara o relatório de referência.
