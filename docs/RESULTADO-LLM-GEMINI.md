# Resultado: Gemini no held-out (1 execução, 13/10/2026)

Gerado pelo workflow `avaliar-llm` (GitHub Actions) e copiado da anotação da execução; as
transcrições ficaram só no artefato `avaliacao-llm` do Actions (expira), **não** neste repositório.

| Item | Valor |
|---|---|
| Modelo / provedor | `gemini-3.5-flash-lite` via Google (plano gratuito, endpoint compatível com OpenAI) |
| Conjunto | held-out, 11 tarefas, 1 trial por tarefa |
| pass@1 = pass^1 | 11/11 = 100,0% |
| Estado alterado / ferramenta inválida | 0 / 0 |
| Uso | 21 chamadas, 30.188 tokens de entrada, 1.151 de saída, 36,5 s de API |
| Referência | o planejador de regras (não é um modelo) acerta 36,4% no mesmo held-out |

## Como ler (e o que NÃO provam estes números)

- **Uma execução, 11 tarefas, 1 trial.** Com n = 11, 11/11 é compatível com uma taxa verdadeira bem menor
  (limite inferior do intervalo de Clopper-Pearson a 95% ≈ 71,5%; conta abaixo). Não é uma
  medida estável.
- **Contaminação provável.** As tarefas e o prompt de sistema foram escritos pela mesma pessoa/sessão, e o
  prompt cita os casos (esclarecimento, recusa, erro). O held-out é "novo" para o planejador de regras,
  não necessariamente para um LLM guiado por esse prompt.
- **Graders por estado final podem ser lenientes.** Nenhuma transcrição foi revisada à mão (o artefato não
  pôde ser baixado deste ambiente). Revisão manual de uma amostra continua pendente.
- O resultado vale para esse modelo e essa data; não diz nada sobre o Claude nem sobre outros modelos.

## Conta do intervalo (conferência)

Para c = n = 11, o limite inferior exato de Clopper-Pearson (bilateral, 95%) é (α/2)^(1/n) com α/2 = 0,025:
0,025^(1/11) = exp(ln 0,025 / 11) = exp(−3,6889 / 11) = exp(−0,33535) = 0,7151.
Logo, **IC 95% ≈ [71,5%; 100%]**.


---

# Rodada 2: 42 tarefas × 3 trials (13/10/2026, mesmo modelo, plano gratuito)

Workflow `avaliar-llm` (provedor gemini, `gemini-3.5-flash-lite`, trials 3, split todos); 238 chamadas, 335.633 tokens de
entrada, 14.890 de saída, 1.211 s de API; ritmo mínimo de 4,5 s entre chamadas. Estado alterado = 0 e ferramenta inválida = 0
nos dois conjuntos.

| Conjunto | Tarefas | pass@1 | pass@3 | pass^3 |
|---|---|---|---|---|
| dev | 31 | 93,5% | 96,8% | 90,3% (28/31) |
| held-out | 11 | 100,0% | 100,0% | 100,0% (11/11) |

## Falhas, uma a uma (transcrições lidas por amostra, como anotações da execução)

| Tarefa | O que o modelo fez | Leitura |
|---|---|---|
| `ng10` (trials 0 e 2) | Pedido sem margem-alvo; o modelo **inventou** `margem_alvo` (0,10 e 0,15) e respondeu `ok` em vez de pedir esclarecimento | Falha real e relevante: parâmetro fabricado. É o achado mais útil da rodada |
| `ng1` (trials 0, 1, 2) | Despesas de 120%: não chamou ferramenta e devolveu `esclarecimento` (pedindo valor válido) em vez de `erro` | Resposta razoável para um humano; o avaliador exige `erro`. Ambiguidade da especificação da tarefa, não do modelo |
| `pj2` (trial 0) | Chamou a ferramenta certa (0 pares no prejuízo) mas devolveu a chave `pares_no_prejuizo` em vez de `total` | Descumpriu o contrato de chaves do prompt; o resultado numérico estava certo |

## Conferência das contas

- dev: pass^3 = 28/31 = 90,3% (confere com a tabela); pass@1 = 93,5% = 29/31 (média por tarefa dos trials).
- Intervalo de Clopper-Pearson 95% (tarefas como unidade, **aproximação**: os 3 trials da mesma tarefa não são independentes):
  held-out 11/11 → [71,5%; 100%]; dev 28/31 → [74,2%; 98,0%]; as 42 tarefas, 39/42 → [80,5%; 98,5%] (calculado com `scipy.stats.beta`).

## FATO × PRÁTICA × HIPÓTESE

- **FATO** (esta execução, 13/10/2026): números acima; a amostra de transcrições (aprovadas e reprovadas) foi lida.
- **PRÁTICA**: relatar pass@k e pass^k com tarefas separadas em dev e held-out e avaliadores por estado final (Anthropic, "Demystifying evals for AI agents"; ver `docs/AVALIACAO.md`).
- **HIPÓTESE**: que o desempenho se mantenha em outros dias ou modelos; que o held-out não esteja contaminado (mesmo autor e prompt de sistema que cita os casos).

## Não verificado

Nenhuma execução com o Claude (sem chave Anthropic); um único modelo e um único dia; tarefas e prompt do mesmo autor; só uma
amostra das transcrições foi lida (as demais ficaram no artefato do Actions, que expira); sem segundo avaliador independente.
