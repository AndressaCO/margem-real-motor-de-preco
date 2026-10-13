# ADR 0002 — Quarentena por linha, com bloqueio por limiar

**Status:** aceito · **Data:** 13/10/2026

**Contexto.** Dados de vendas chegam com linhas ruins (preço zero, SKU inexistente, mês mal
formado). Derrubar o lote por uma linha trava o fechamento; descartar em silêncio corrompe a margem.

**Decisão.** Violação estrutural (coluna ausente, tipo errado) derruba o lote. Violação por linha
vai para a tabela `quarentena` com motivo e conteúdo. Se a taxa de rejeição passa de 5% ou o
volume cai mais de 50% contra o último lote aceito, o lote inteiro é bloqueado com rollback.

**Consequências.** Invariante verificado em teste: entrada = carregadas + quarentena. Um erro
sistêmico (coluna de preço em centavos, por exemplo) vira bloqueio, não 100% de dados ruins
carregados. Os limiares são premissas; em produção devem vir de um histórico de lotes aceitos.
