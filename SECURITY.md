# Segurança e privacidade

- **Dados:** 100% sintéticos (ver `DATASHEET.md`). Não há dado pessoal nem de empresa. Não envie dados reais por issue ou pull request.
- **Segredos:** o repositório não contém chaves, tokens nem senhas, e o código não lê variáveis de ambiente de credenciais. A auditoria (`scripts/auditar.py`) procura padrões comuns de segredo a cada execução; isso reduz o risco, não o elimina.
- **Agente:** todas as ferramentas são somente leitura e há teste que prova que o estado do armazém não muda. Resultado de ferramenta é tratado como dado, nunca como instrução (teste dedicado).
- **Dependências:** versões travadas em `requirements-dev.lock` e atualização semanal via Dependabot. Varredura de vulnerabilidades (por exemplo `pip-audit`) **não** foi executada neste ambiente; ver `VERIFICACAO.md`.
- **LGPD:** ao usar com dados reais de clientes ou funcionários, faça revisão de LGPD antes (finalidade, base legal, minimização). Este projeto não trata dados pessoais.
- **Reportar problema:** abra uma issue sem dados sensíveis.
