# ADR 0003 — Agente somente leitura e planejador plugável

**Status:** aceito · **Data:** 13/10/2026

**Contexto.** Quero demonstrar como se constrói e se AVALIA um agente de IA sobre dados
financeiros, sem exigir chave de API e sem risco de o agente alterar dados.

**Decisão.**
1. Todas as ferramentas são somente leitura; um teste prova que o estado do armazém não muda.
2. O planejador é uma interface (`proximo(pergunta, historico) -> Passo`). O repositório traz um
   planejador determinístico por regras (stand-in) e um planejador ruidoso (injeção de falhas
   para validar o harness). Um LLM entra implementando a mesma interface.
3. A avaliação julga o desfecho (status, valores, estado), com referências independentes do
   código das ferramentas, e separa tarefas de desenvolvimento das held-out.

**Consequências.** Os números do planejador de regras NÃO medem nenhum modelo. O que o
repositório entrega é o harness e a disciplina de avaliação. Ligar um LLM é trabalho futuro e
declarado, não implícito.
