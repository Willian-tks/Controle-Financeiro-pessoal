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

## Atualizações recentes
- Hoje foi evoluída a área de `Investimentos > Resumo > Preço justo e viés`.
- A regra agora separa:
  - sinal técnico automático (`Comprar`, `Aguardar`, `Vender`)
  - objetivo manual do usuário (`Acumular`, `Segurar`, `Reduzir`, `Sair`)
- O backend e o banco passaram a persistir `user_objective` no cadastro do ativo.
- A tabela de preço justo ganhou:
  - badges mais compactos para sinal técnico e objetivo
  - edição inline do `Preço justo` na própria linha
  - ação de exclusão da configuração de preço justo
  - melhoria visual dos botões de ação
  - troca do ícone de download para SVG real no botão do relatório PDF
- A carteira consolidada também passou a exibir `Custo médio` por ativo.
- Como houve mudança de backend, banco e frontend, novas sessões que mexerem nessa área devem considerar:
  - migração automática da coluna `user_objective` ao subir o backend
  - rebuild do frontend para refletir ajustes visuais e novos assets
- Foi definida uma proposta oficial para um novo módulo `Listas`, com foco em organização pessoal simples dentro do DOMUS.
- Os documentos base preparados para iniciar a implementação são:
  - `PROPOSTA_MODULO_LISTAS_DOMUS.md`
  - `BACKLOG_MODULO_LISTAS_DOMUS.md`
  - `CHECKLIST_MODULO_LISTAS_DOMUS.md`
- Decisões já fechadas para esse módulo:
  - nome final: `Listas`
  - escopo por `workspace_id`
  - V1 sem integração automática com financeiro
  - V1 sem recorrência, modelos, valor real pago ou metas complexas
  - item com `sort_order` e `completion_date` já previstos desde a primeira versão
- Ao retomar Listas, consultar o status executivo de `BACKLOG_MODULO_LISTAS_DOMUS.md`: o MVP já está implementado; priorizar validação e rollout pendentes, sem reiniciar a Fase 1.

## Planejamento versionado — 2026-09-21

- O planejamento da versão-alvo 1.5.0 está em `Backlog1.5.md`, com prioridades, dependências e critérios de aceite.
- Consultar esse documento antes de iniciar melhorias gerais; ele não implica que a versão 1.5 esteja implementada ou publicada.
- Para Listas, consultar o status do `BACKLOG_MODULO_LISTAS_DOMUS.md`: a orientação antiga de começar pela Fase 1 está superada pelo backlog revisado. Validar pendências antes de iniciar nova implementação.
- Atualizar o estado e as evidências dos itens durante a execução e registrar a versão/commit efetivamente publicados.

## Preparação de release — 2026-10-26

- Versão candidata local: `1.5.0-rc.1`. Não equivale à publicação da versão final 1.5.0.
- Fonte da identidade do produto: `frontend/src/productVersion.json`, consumida pelo frontend e por `product_version.py` na API; manter package.json e lockfile alinhados.
- Status atual e bloqueios em `Backlog1.5.md`; resumo da entrega em `CHANGELOG.md` e checklist em `RELEASE_1.5.md`.
- 007 continua em validação; 008 aprovado localmente; 009 é especificação em `AI_DRAFT_CONTRACT.md`, não integração ativa.
- Não encerrar 002 sem decisão explícita sobre os registros legados; não declarar 010 concluído antes de CI, publicação e conferência no VPS.
