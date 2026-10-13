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
