# Como o agente é avaliado

## Objeto avaliado

Um agente de consulta **somente leitura** sobre o armazém de margens, com 6 ferramentas (`margem_resumo_por_canal`, `margem_pares_no_prejuizo`, `margem_calcular_preco_minimo`, `margem_calcular_preco_sugerido`, `margem_reprecificar_par`, `margem_conciliar`). O planejador é plugável (`Planejador`, um `Protocol`).

**O planejador incluído, `PlanejadorRegras`, é um stand-in determinístico baseado em regex. Não é um modelo de linguagem.** Ele existe para que o harness rode de ponta a ponta e seja testável sem custo. Nenhuma métrica aqui descreve um LLM.

## Princípios (e a fonte de cada um)

| Princípio | Como está implementado | Fonte |
|---|---|---|
| Avaliar o resultado, não o caminho | Graders checam `status`, valores e o hash do estado do banco ao final | Anthropic, *Demystifying evals for AI agents* |
| Referência independente das ferramentas | Valores esperados vêm de pandas + `Fraction` e de constantes calculadas à mão, nunca das próprias ferramentas | idem |
| Ambiente limpo por trial | `novo_ambiente()` recria o armazém a cada trial | idem |
| Salvar transcrições | `evals/transcripts/*.jsonl` versionados | idem |
| Casos negativos | Recusas (escrita, dados inexistentes), pedidos ambíguos, limites de truncagem | idem |
| Evitar saturação | Conjunto **held-out**, escrito depois do planejador | idem |
| Eficiência e ferramenta inválida só informativas | Não reprovam a tarefa | idem |
| Ferramentas com erro acionável e truncagem com `total` | `ferramentas.chamar` | Anthropic, *Writing tools for agents* |

## Métricas

- `pass@k = 1 − C(n−c, k)/C(n, k)` — chance de ao menos 1 de k tentativas passar (Chen et al., 2021, arXiv:2107.03374).
- `pass^k = C(c, k)/C(n, k)` — chance de **todas** as k passarem (τ-bench, arXiv:2406.12045).
- n = 5 trials por tarefa. Calculadas com `fractions.Fraction`; antes disso, `pass@1` devolvia `0.19999999999999996`.

## Resultados atuais

Ver o bloco gerado no [README](../README.md) e o relatório completo em [`evals/RELATORIO.md`](../evals/RELATORIO.md).

Leitura:

- **dev 100%**: esperado, pois o planejador foi escrito olhando essas tarefas. Não mede generalização.
- **held-out 36,4%** (4 de 11): o número que importa. Falhas: `h1, h3, h4, h5, h9, h11` por roteamento (o planejador devolve esclarecimento ou recusa em vez do resultado) e `h2` com **resposta silenciosamente errada** (87,5 em vez de 96,88, ignorando o custo fixo). Este último é o tipo de falha que um grader só de formato não pegaria.
- **ruidoso**: injeta erro em 25% das chamadas. `pass^5` cai a 6,5% no dev, o que confirma que o harness enxerga falhas intermitentes que `pass@k` mascararia.

## Avaliar um LLM real (implementado; 2 execuções feitas, com ressalvas)

Resultado das duas execuções (Gemini; rodada 2: 42 tarefas × 3 trials, dev pass^3 90,3%, held-out 11/11): `docs/RESULTADO-LLM-GEMINI.md`. Leia as ressalvas antes de citá-lo.

`PlanejadorClaude` (`src/margem_real/agent/llm.py`) é um `Planejador` que chama a API Messages da Anthropic. O modelo recebe as 6 ferramentas `margem_*` e uma 7ª, `responder(status, texto, dados)`, que encerra o atendimento; os avaliadores por estado final são os mesmos do stand-in. A chave vem de `ANTHROPIC_API_KEY`.

**Gratuito, plano gratuito do Gemini (Google):** crie uma chave em aistudio.google.com e guarde-a como secret `GEMINI_API_KEY`; depois `Actions > avaliar-llm > Run workflow` com `provedor=gemini` e um modelo listado no AI Studio. Usa o endpoint compatível com OpenAI (`generativelanguage.googleapis.com/v1beta/openai/`) com chamada de função. FATO (documentação do Google consultada em 13/10/2026): o plano gratuito existe e os limites atuais só aparecem no AI Studio, então não os cito; a compatibilidade com OpenAI está em beta e o `tool_choice` documentado é só `"auto"`. NÃO verificado: execução real, limites da sua conta, nome de modelo disponível (o `gemini-3.8-flash` do padrão é o exemplo da documentação), uso dos dados do plano gratuito. O resultado vale para o Gemini, não para o Claude.

**GitHub Models (tentado e descartado):** foi a primeira escolha por não exigir chave (usaria o `GITHUB_TOKEN` do Actions). Em 13/10/2026 o endpoint respondeu HTTP 200 `text/plain` com `OK` em vez de JSON e a página da API REST do GitHub diz que o serviço foi encerrado em 30/07/2026 (uma única fonte; o comportamento observado é coerente com ela). Ficaram de lição as páginas de blogs e agregadores que ainda o listavam como gratuito: estavam desatualizadas.

**Pago, Anthropic (opcional):**

1. Em *Settings > Secrets and variables > Actions*, crie o secret `ANTHROPIC_API_KEY`.
2. Em *Actions > avaliar-llm > Run workflow*, informe o modelo (ex.: `claude-sonnet-5-5`), `trials` (padrão 3) e `split` (`heldout`, `dev` ou `todos`).
3. O relatório aparece no resumo da execução; relatório, resultados e transcrições ficam no artefato `avaliacao-llm`.

**Local:** `ANTHROPIC_API_KEY=... python -m margem_real.agent.evals --llm-modelo <id> --trials 3 --split heldout`. A saída vai para `evals/llm/<modelo>/` e **não** altera `evals/resultados.json` (que continua sendo o resultado determinístico, sem chave).

**Custo:** cresce com tarefas × trials × passos. Comece por `heldout` com 1–3 trials.

**O que foi verificado:** encanamento ponta a ponta com um cliente falso que reproduz o `PlanejadorRegras` pela interface da API (dev pass^2 = 100%, nenhum estado alterado), leitura de resposta, repetição em 429, e que a chave não vaza em erros (11 testes em `tests/test_llm.py`).

**O que NÃO foi verificado:** execução com o Claude (Anthropic) ou com mais de um modelo, repetição entre dias, revisão manual das transcrições, o formato exato de resposta da API em produção além do documentado, custo e latência reais, e a qualidade do prompt de sistema. Depois de rodar: revise à mão uma amostra das transcrições (avaliadores automáticos também erram) e registre o resultado em `VERIFICACAO.md`.

Limites de interpretação: uma execução única de um modelo é uma medida pontual; ela varia com a versão do modelo, a temperatura e a carga da API.
