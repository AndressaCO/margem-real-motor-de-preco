# Verificação

Primeira rodada: 13/10/2026 (código e contas). Segunda rodada: 13/10/2026 (fontes, parâmetros e versões de Python).
Ambiente: Python 3.13 (principal), 3.12 e 3.11; pandas 3.0.5, DuckDB 1.5.6, pytest 9.1.1, ruff.

## 1. Código e contas (verificado)

| Item | Como | Resultado |
|---|---|---|
| Fórmulas de preço mínimo, sugerido e margem | Conta manual no teste (`100/0,66 = 151,52`; `100/0,56 = 178,58`; `56/0,64 = 87,50`) | Confere |
| Invariantes: margem no preço mínimo ≥ 0; no sugerido ≥ alvo | 4 custos × 3 níveis de despesa, com e sem taxa fixa | Confere |
| SQL × Python | Preço mínimo e margem de 40 pares recalculados em `pricing.py` | Diferença < R$ 0,011 e < 0,2 p.p. |
| Identidade contábil | receita − CMV − despesas = margem, linha a linha | Erro máximo < R$ 0,02 |
| Números do relatório | Recontagem independente em pandas puro | Receita idêntica (R$ 1.671.731,82) e 667 pares; margem R$ 182.257,91 contra R$ 182.257,81 no SQL |
| Versões de Python | `pytest` + `ruff` em ambiente novo, em 3.11, 3.12 e 3.13 | 26 aprovados e ruff limpo nas três |
| Reprodutibilidade | Mesma semente gera os mesmos dados; instalação limpa gera o mesmo relatório | Confere |

**Divergência registrada:** os R$ 0,10 na margem total vêm do `ROUND(…, 2)` por linha no SQL; o pandas soma sem arredondar. Não afeta conclusão alguma.

## 2. Parâmetros de canal contra fontes (verificado em 13/10/2026)

**Imposto — FATO (fonte oficial).** Anexo I da LC 123/2006 (Simples Nacional, comércio), redação da LC 155/2016, vigência 01/01/2018 (com remissão à LC 214/2025): <https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm>.

| Faixa | Receita bruta em 12 meses (RBT12) | Alíquota nominal | Valor a deduzir |
|---|---|---|---|
| 1ª | até R$ 180.000,00 | 4,00% | — |
| 2ª | até R$ 360.000,00 | 7,30% | R$ 5.940,00 |
| 3ª | até R$ 720.000,00 | 9,50% | R$ 13.860,00 |
| 4ª | até R$ 1.800.000,00 | 10,70% | R$ 22.500,00 |
| 5ª | até R$ 3.600.000,00 | 14,30% | R$ 87.300,00 |
| 6ª | até R$ 4.800.000,00 | 19,00% | R$ 378.000,00 |

Alíquota efetiva = (RBT12 × alíquota − deduzir) / RBT12. Conta refeita: R$ 500 mil → 6,73%; R$ 1 milhão → 8,45%; R$ 1,8 milhão → 9,45%; R$ 3,6 milhões → 11,87%; R$ 4,8 milhões → 11,12%.

- O `imposto` de 8% (marketplaces e site) corresponde a uma empresa com RBT12 em torno de R$ 1 milhão. O de 10% (B2B) cabe em RBT12 entre R$ 1,8 e R$ 3,6 milhões.
- **Inconsistência assumida:** no Simples a alíquota efetiva é a mesma para todos os canais da empresa; eu usei 8% e 10% por canal só para dar variação didática. O resultado por canal mistura, portanto, efeito de imposto e de estrutura de custo. Empresas fora do Simples, ou com ST/DIFAL, têm outra conta. Revisão de contador necessária.

**Comissão e taxa fixa — PRÁTICA DE MERCADO (fonte secundária).**

| Marketplace | O que a fonte diz | Fonte e data |
|---|---|---|
| Shopee | Item até R$ 79,99: 20% + R$ 4 por item. Acima de R$ 80: 14% + R$ 16 a R$ 26 por item (conforme a faixa). CPF paga +R$ 3 por item. | ecommercenapratica.com, atualizada em 28/07/2026 |
| Mercado Livre | Comissão de 10% a 14% (clássico) e 15% a 19% (premium). O custo fixo foi substituído em março/2026 por tarifa variável por peso e faixa de preço (a partir de R$ 19). | ecommercenapratica.com, atualizada em 29/07/2026 |

O `marketplace_a` (16% de comissão + R$ 6 fixos) e o `marketplace_b` (12%) ficam na mesma ordem de grandeza, mas **não replicam** nenhuma tabela. Continuam ilustrativos, como o README declara.

## 3. Referências reabertas (verificado em 13/10/2026)

| Fonte | Abriu? | O que confirma |
|---|---|---|
| Data Engineer Academy, "Data Engineer Portfolio Review Checklist (2026)", Chris Garzon, publicado 28/01/2026, atualizado 02/02/2026 | Sim | Avaliadores leem o README primeiro; valorizam dados realistas, validações e testes, e impacto mensurável ligado a problema de negócio |
| Placement Preparation, "GitHub Profile & Portfolio Guide", publicado 26/05/2026, atualizado 02/06/2026 | Sim | README de perfil em repositório público com o nome do usuário; até 6 projetos fixados; cada projeto com README de o quê, como e por quê |
| GitHub Docs, "Managing your profile README" (oficial; a página não traz data) | Sim | Requisitos: repositório público com o mesmo nome do usuário e `README.md` na raiz com conteúdo |
| Vagas.com.br, "analista de BI" | Sim | 10 vagas; Power BI citado em 9; Excel em 2; SAP em 3; **SQL e Python não aparecem** nos trechos (que são truncados) |
| Empregando Brasil, Analista de Power BI, 03/06/2026 | Sim | 1 vaga: DAX e Power Query (2 menções cada), SQL (requisito), Python (diferencial) |
| Virtual Vocations, Senior Analytics Analyst | Sim, mas **vaga expirada** | Remota; SQL, Python, Snowflake, Databricks e ferramentas de IA; revisada em 06/07/2026 |

**Correções à primeira rodada:**
1. A vaga remota **não cita DAX nem Power Query M**; cita SQL, Python, Snowflake e Databricks. DAX e Power Query aparecem na vaga do Empregando Brasil.
2. Nas listagens do Vagas.com.br, a demanda dominante é **Power BI**. SQL e Python entram só pelas outras duas fontes.
3. A vaga do Virtual Vocations está expirada, então vale como exemplo de requisito, não como oportunidade aberta.

## 4. FATO × PRÁTICA DE MERCADO × HIPÓTESE

| Classe | Afirmação | Fonte e data |
|---|---|---|
| FATO | Preço mínimo = (c+f)/(1−d); sugerido = (c+f)/(1−d−m) | Derivação algébrica + testes, 13/10/2026 |
| FATO | Alíquotas do Anexo I do Simples (comércio) e as alíquotas efetivas calculadas | Planalto (LC 123/2006, redação LC 155/2016), consultado em 13/10/2026 |
| FATO | Requisitos do README de perfil no GitHub | GitHub Docs, consultado em 13/10/2026 |
| FATO (empírico, local) | Com semente 42, 95 de 667 pares ficam abaixo do mínimo | Execução do código, 13/10/2026 |
| PRÁTICA DE MERCADO | Recrutadores valorizam poucos projetos com pergunta de negócio, README claro, testes e impacto | Data Engineer Academy (2026); Placement Preparation (2026) |
| PRÁTICA DE MERCADO | Vagas de BI pedem Power BI, DAX, Power Query, SQL; Python como diferencial; vaga remota sênior pede SQL, Python, Snowflake/Databricks | Vagas.com.br, Empregando Brasil (03/06/2026), Virtual Vocations (06/07/2026) |
| PRÁTICA DE MERCADO | Tarifas Shopee e Mercado Livre da seção 2 | ecommercenapratica.com, 28 e 29/07/2026 |
| HIPÓTESE | Este portfólio aumenta a taxa de convites para entrevistas | Sem teste. Medir: visitas e convites em 30 dias |
| HIPÓTESE | Dados sintéticos com método aberto convencem mais que descrição sem código | Sem teste |

## 5. O que continua NÃO verificado

- **Tarifas oficiais dos marketplaces.** A página oficial de tarifas do Mercado Livre bloqueia leitura automática (robots), e não consultei a central de vendedores da Shopee. Os valores vêm de blog.
- **Eficácia do portfólio.** Nenhuma fonte quantifica o efeito de um portfólio no GitHub sobre entrevistas; as fontes são qualitativas.
- **Amostra de vagas.** São 12 vagas em 3 páginas, com trechos truncados, sem recorte estatístico.
- **Regime tributário real.** O projeto não trata ST, DIFAL, fator R, nem a transição CBS/IBS da LC 214/2025.
- **CI no GitHub.** O workflow existe, mas só roda após o primeiro push. Windows e macOS não foram testados.
- **Links do README do perfil.** Usuário do GitHub (`AndressaCO`) confirmado pela API; LinkedIn e site vieram da sua informação e não foram abertos. O link do repositório só funciona depois da publicação.

## 6. Sobre "top 0,01%"

Este material **não afirma** esse posicionamento. Não há métrica que classifique candidatos nesse percentil, e as evidências são qualitativas. O que se sustenta: o projeto cumpre os critérios que as fontes citam como diferenciais (pergunta de negócio, conta aberta, testes, limites declarados).
