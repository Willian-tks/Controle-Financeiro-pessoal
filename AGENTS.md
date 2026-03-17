# DOMUS Project Guide

## Context
- Este repositório é o projeto `DOMUS`.
- O sistema está em produção controlada no VPS, com poucos usuários e ajustes incrementais conforme o uso.
- O fluxo principal de trabalho é: ajuste local -> validação local -> commit/push para o Git -> deploy no VPS.
- Mudanças devem priorizar segurança, compatibilidade com a base atual e baixo risco de regressão.

## Stack
- Backend: FastAPI com entrada principal em `api.main:app`
- Frontend: React 18 + Vite em `frontend/`
- Banco local de desenvolvimento: SQLite em `data/finance.db`
- Produção: VPS com Nginx + systemd; suporte a PostgreSQL via `DATABASE_URL`

## Estrutura principal
- `api/`: API HTTP e schemas
- `frontend/`: aplicação web React/Vite
- `tests/`: testes automatizados
- `deploy/nginx/`: configuração de Nginx
- `deploy/systemd/`: serviço do backend no VPS
- `run_local.ps1`: sobe backend e frontend localmente
- `VPS_LOCALWEB_DEPLOY.md`: guia operacional de deploy no VPS

## Como rodar localmente
- Preferir `run_local.ps1` para iniciar o ambiente completo.
- Backend local esperado em `http://127.0.0.1:8000`
- Frontend local esperado em `http://127.0.0.1:5173`
- No desenvolvimento local, o script força SQLite com `LOCAL_DEV_FORCE_SQLITE=1`.

## Comandos úteis
- Backend: `python -m uvicorn api.main:app --reload --port 8000`
- Frontend dev: `cd frontend` e `npm run dev`
- Frontend build: `cd frontend` e `npm run build`
- Testes Python: `python -m unittest discover -s tests -p "test_*.py" -v`

## Regras de trabalho para este projeto
- Antes de editar, entender o impacto no fluxo já em produção.
- Não alterar `.env` com valores reais nem expor segredos em respostas.
- Não assumir que deploy é automático; considerar sempre o fluxo Git -> VPS.
- Evitar refatorações amplas sem necessidade funcional clara.
- Em correções sensíveis, preferir mudanças pequenas, rastreáveis e fáceis de reverter.
- Se houver mudança que afete deploy, também revisar arquivos em `deploy/` e a documentação operacional.

## Fluxo esperado com o usuário
- No início de uma sessão, confirmar o objetivo do ajuste do dia.
- Ao trabalhar em uma tarefa, primeiro mapear os arquivos impactados.
- Sempre que possível, validar localmente o trecho alterado.
- Ao finalizar, informar:
  - o que mudou
  - como validar
  - se há impacto no deploy para o VPS

## Produção e deploy
- O VPS serve o frontend buildado em `frontend/dist`.
- O backend roda via `systemd`.
- O Nginx entrega o frontend e faz proxy para a API.
- O arquivo `render.yaml` é histórico e não é a referência principal do ambiente atual.
- A referência operacional para deploy é `VPS_LOCALWEB_DEPLOY.md`.

## Prioridades
- Primeiro: corrigir bugs e manter estabilidade para os usuários atuais.
- Segundo: preservar consistência entre ambiente local e VPS.
- Terceiro: melhorar a base sem criar risco desnecessário.
