-- Margem de contribuição por SKU x canal (DuckDB).
-- Tabelas esperadas: vendas(sku, canal, mes, unidades, preco),
--                    skus(sku, categoria, custo), canais(canal, pct_despesas, custo_fixo).
--
-- margem de contribuição = receita - CMV - despesas proporcionais - custo fixo por unidade
-- preço mínimo           = (custo + fixo) / (1 - pct_despesas)   -- ponto de equilíbrio

WITH agregado AS (
    SELECT
        v.sku,
        s.categoria,
        v.canal,
        s.custo,
        c.pct_despesas,
        c.custo_fixo,
        SUM(v.unidades)               AS unidades,
        SUM(v.unidades * v.preco)     AS receita
    FROM vendas v
    JOIN skus   s ON s.sku   = v.sku
    JOIN canais c ON c.canal = v.canal
    GROUP BY v.sku, s.categoria, v.canal, s.custo, c.pct_despesas, c.custo_fixo
)
SELECT
    sku,
    categoria,
    canal,
    unidades,
    ROUND(receita, 2)                                                AS receita,
    ROUND(unidades * custo, 2)                                       AS cmv,
    ROUND(receita * pct_despesas + unidades * custo_fixo, 2)         AS despesas_variaveis,
    ROUND(receita - unidades * custo
          - receita * pct_despesas - unidades * custo_fixo, 2)       AS margem_contribuicao,
    (receita - unidades * custo
        - receita * pct_despesas - unidades * custo_fixo) / receita  AS margem_pct,
    custo,
    CEIL((custo + custo_fixo) / (1 - pct_despesas) * 100) / 100      AS preco_minimo,
    ROUND(receita / unidades, 2)                                     AS preco_medio_praticado
FROM agregado
ORDER BY margem_contribuicao;
