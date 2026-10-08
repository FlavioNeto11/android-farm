# Instruções para o GitHub Copilot

## Estrutura e comandos

- O backend usa FastAPI e SQLAlchemy, com módulos organizados por domínio em `backend/app/modules`; os endpoints ficam em `backend/app/api`.
- O frontend usa React, TypeScript e Vite em `frontend/src`.
- Testes do backend: na raiz, instale `backend/requirements.txt` e `backend/requirements-dev.txt`; depois execute `python -m pytest tests/` dentro de `backend`.
- Frontend: execute `npm ci`, `npm run typecheck` e `npm run build` dentro de `frontend`.
- Faça mudanças pequenas, mantenha os testes relevantes e não adicione dependências sem necessidade.

## Segurança e uso responsável

- Nunca inclua credenciais, tokens, chaves, dados pessoais ou segredos reais em código, testes, logs, issues, pull requests ou exemplos. Use apenas valores sintéticos.
- Não leia, imprima ou exponha arquivos `.env`, chaves privadas ou dados de runtime; arquivos em `data/`, `logs/` e segredos não devem ser enviados ao Git.
- Não tente contornar CAPTCHA, limites, verificações, mecanismos antiabuso ou outras proteções das plataformas. Qualquer automação deve ser autorizada e respeitar os termos e políticas aplicáveis.
- Ao alterar armazenamento, API ou tratamento de logs, considere exposição de credenciais e inclua testes que usem diretórios e dados temporários.
