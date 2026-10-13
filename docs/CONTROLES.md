# Matriz de controles (visão de controladoria)

Estrutura inspirada nos cinco componentes do COSO 2013 (ambiente de controle, avaliação de
riscos, atividades de controle, informação e comunicação, monitoramento; 17 princípios). Aqui
só as **atividades de controle** e o **monitoramento** são exercitados em código. O restante
(ambiente de controle, segregação de funções, alçadas) depende de organização real e **não é
demonstrado** neste repositório.

| # | Risco | Controle | Tipo | Evidência no repositório | Frequência sugerida | Responsável sugerido |
|---|---|---|---|---|---|---|
| C1 | Carga duplicada infla a receita | Lote identificado por hash; reenvio ignorado | Preventivo, automático | `test_reenvio_do_mesmo_lote_nao_altera_nada` | A cada carga | Engenharia de dados |
| C2 | Linha inválida distorce a margem | Contrato por linha + quarentena com motivo | Preventivo, automático | `test_invariante_entrada_igual_carregadas_mais_quarentena` | A cada carga | Engenharia de dados |
| C3 | Erro sistêmico na origem | Bloqueio por taxa de rejeição e queda de volume | Detectivo, automático | `test_lote_acima_do_limite...`, `test_baseline_de_volume...` | A cada carga | Engenharia de dados |
| C4 | Camada de consumo não fecha com o bruto | Conciliação de receita e unidades com tolerância | Detectivo, automático | `test_conciliacao_fecha...`, `..._detecta_divergencia` | A cada carga e no fechamento | Controladoria |
| C5 | Dado desatualizado alimenta decisão | Teste de frescor contra SLA | Detectivo, automático | `test_frescor_respeita_o_sla` | Diária | Controladoria |
| C6 | Não saber de onde veio um número | `lote_id` em cada linha; trilha de execuções | Detectivo, rastreabilidade | `test_linhagem_aponta_o_lote_de_origem` | Sob demanda | Auditoria interna |
| C7 | Preço abaixo do equilíbrio | Preço mínimo com teto ao centavo | Preventivo | Testes de propriedade (Hypothesis) | A cada reprecificação | Comercial + Controladoria |
| C8 | Agente altera dado ou preço | Ferramentas somente leitura; hash do estado antes/depois | Preventivo | `test_nenhuma_ferramenta_escreve` e avaliador de estado | A cada execução | Quem opera o agente |
| C9 | Imposto aplicado de forma incoerente | Alíquota efetiva única do Simples (`--rbt12`) | Preventivo | `tests/test_tributos.py` | A cada mudança de faixa/regime | Contador |

## Limites (não verificados)

- Tolerância da conciliação (R$ 0,005 por par) é decisão técnica; a política de materialidade real é da empresa.
- Os responsáveis são sugestões; **não há segregação de funções real** neste projeto.
- Nada aqui substitui parecer de contador, auditor ou advogado, nem revisão de LGPD em dados reais.
