# ADR 0001 — DuckDB embarcado como armazém

**Status:** aceito · **Data:** 13/10/2026

**Contexto.** O projeto precisa de SQL analítico reproduzível por qualquer pessoa, sem servidor,
senha ou custo, e com restrições de integridade (chave primária, CHECK, transação).

**Decisão.** Usar DuckDB (arquivo local ou memória) para o armazém e para a camada de consumo.

**Alternativas.** PostgreSQL/Supabase (mais realista para produção, mas exige serviço e segredos
no repositório de portfólio); SQLite (sem a ergonomia analítica); só pandas (sem restrições
declarativas nem SQL auditável).

**Consequências.** Reprodutível com `pip install`. Não demonstra concorrência de escritores,
permissões por papel nem replicação. O SQL é padrão o bastante para migrar para Postgres; a
diferença relevante é `ON CONFLICT`, que ambos suportam.
