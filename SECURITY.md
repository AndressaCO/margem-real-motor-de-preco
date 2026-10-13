# Segurança e privacidade

- **Dados:** 100% sintéticos (ver `DATASHEET.md`). Não há dado pessoal nem de empresa. Não envie dados reais por issue ou pull request.
- **Segredos:** o repositório não contém chaves, tokens nem senhas, e as únicas credenciais que o código lê são `ANTHROPIC_API_KEY` ou `GEMINI_API_KEY`, e só ao rodar a avaliação com LLM (`--llm-modelo`); ela vem de variável de ambiente ou do secret do GitHub, nunca é gravada em transcrição, relatório ou log, e os erros de API não a repetem (há teste). Na nuvem, o workflow `avaliar-llm` é manual (`workflow_dispatch`), não roda em PR nem em push e usa permissões mínimas (`contents: read`). A auditoria (`scripts/auditar.py`) procura padrões comuns de segredo a cada execução; isso reduz o risco, não o elimina.
- **Agente:** todas as ferramentas são somente leitura e há teste que prova que o estado do armazém não muda. Resultado de ferramenta é tratado como dado, nunca como instrução (teste dedicado).
- **Dependências:** versões travadas em `requirements-dev.lock` e atualização semanal via Dependabot. Varredura de vulnerabilidades (por exemplo `pip-audit`) **não** foi executada neste ambiente; ver `VERIFICACAO.md`.
- **LGPD:** ao usar com dados reais de clientes ou funcionários, faça revisão de LGPD antes (finalidade, base legal, minimização). Este projeto não trata dados pessoais.
- **Reportar problema:** abra uma issue sem dados sensíveis.
