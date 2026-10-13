# Relatório de avaliação do agente (gerado por `python -m margem_real.agent.evals`)

Tarefas: 42 · trials por tarefa: 5 · ambiente isolado por trial.
Não edite à mão: este arquivo é sobrescrito a cada execução.

## Métricas

| Planejador | Conjunto | Tarefas | pass@1 | pass@3 | pass@5 | pass^1 | pass^3 | pass^5 |
|---|---|---|---|---|---|---|---|---|
| regras | dev | 31 | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% | 100,0% |
| regras | heldout | 11 | 36,4% | 36,4% | 36,4% | 36,4% | 36,4% | 36,4% |
| ruidoso(p=0.25) | dev | 31 | 68,4% | 97,1% | 100,0% | 68,4% | 28,4% | 6,5% |
| ruidoso(p=0.25) | heldout | 11 | 25,5% | 36,4% | 36,4% | 25,5% | 9,1% | 0,0% |

- **dev**: tarefas usadas enquanto o planejador de regras era escrito. **heldout**: escritas
  depois, sem ajustar o planejador a elas (mede generalização).
- `regras` é um stand-in determinístico de um LLM (regex sobre texto), não um modelo.
  `ruidoso` injeta falhas sintéticas com taxa conhecida para provar que o harness detecta falha.
  Nenhum número aqui mede um modelo de linguagem.
- pass@k: chance de pelo menos 1 de k trials passar; pass^k: chance de todos os k passarem.

## Por categoria

| Planejador | Conjunto | Categoria | Taxa de aprovação (por trial) |
|---|---|---|---|
| regras | dev | canal | 100,0% |
| regras | dev | controle | 100,0% |
| regras | dev | esclarecimento | 100,0% |
| regras | dev | limite | 100,0% |
| regras | dev | negativo | 100,0% |
| regras | dev | preco_minimo | 100,0% |
| regras | dev | preco_sugerido | 100,0% |
| regras | dev | prejuizo | 100,0% |
| regras | dev | reprecificar | 100,0% |
| regras | heldout | heldout_limite | 100,0% |
| regras | heldout | heldout_multipasso | 0,0% |
| regras | heldout | heldout_negativo | 100,0% |
| regras | heldout | heldout_parafrase | 25,0% |
| ruidoso(p=0.25) | dev | canal | 70,0% |
| ruidoso(p=0.25) | dev | controle | 80,0% |
| ruidoso(p=0.25) | dev | esclarecimento | 80,0% |
| ruidoso(p=0.25) | dev | limite | 73,3% |
| ruidoso(p=0.25) | dev | negativo | 72,0% |
| ruidoso(p=0.25) | dev | preco_minimo | 68,0% |
| ruidoso(p=0.25) | dev | preco_sugerido | 50,0% |
| ruidoso(p=0.25) | dev | prejuizo | 80,0% |
| ruidoso(p=0.25) | dev | reprecificar | 53,3% |
| ruidoso(p=0.25) | heldout | heldout_limite | 60,0% |
| ruidoso(p=0.25) | heldout | heldout_multipasso | 0,0% |
| ruidoso(p=0.25) | heldout | heldout_negativo | 60,0% |
| ruidoso(p=0.25) | heldout | heldout_parafrase | 20,0% |

## Falhas do planejador de regras no conjunto held-out (1ª ocorrência por tarefa)

- `h1`: status='esclarecimento' esperado em ('ok',); preco_minimo: obtido=None esperado=151.52±0.005
- `h2`: preco_minimo: obtido=87.5 esperado=96.88±0.005
- `h3`: status='recusa' esperado em ('ok',); preco_sugerido: obtido=None esperado=178.58±0.005
- `h4`: status='recusa' esperado em ('ok',); canal: obtido=None esperado='marketplace_a'±0
- `h5`: status='esclarecimento' esperado em ('ok',); total: obtido=None esperado=42±0
- `h9`: status='esclarecimento' esperado em ('ok',); preco_minimo: obtido=None esperado=151.52±0.005
- `h11`: status='esclarecimento' esperado em ('ok',); preco_sugerido: obtido=None esperado=28.21±0.005

## Controles de processo (devem ser zero)

- regras / dev: estado alterado = 0, ferramenta inválida = 0
- regras / heldout: estado alterado = 0, ferramenta inválida = 0
