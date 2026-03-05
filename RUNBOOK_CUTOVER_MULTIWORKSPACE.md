# Runbook de Cutover - Multiworkspace DOMUS

Data base: 2026-03-05

## 1. Objetivo

Concluir o rollout de multiworkspace com baixo risco, em 2 releases:

1. `Release 1` (dual mode): mantém fallback legado e monitora comportamento.
2. `Release 2` (enforcement): remove fallback e força `workspace_id NOT NULL`.

## 2. Pré-requisitos

- Backup lógico do banco concluído antes da janela.
- Build backend e frontend validados.
- Endpoints críticos disponíveis:
  - `POST /auth/login`
  - `GET /workspaces`
  - `POST /workspaces/switch`
  - `GET /admin/security/summary` (SUPER_ADMIN)
- Relatório de plano de execução gerado:
  - `MULTIWORKSPACE_EXPLAIN_AUDIT.md`

## 3. Release 1 (dual mode)

Objetivo: confirmar estabilidade sem quebrar usuários existentes.

Checklist:

- Deploy backend com monitoramento de eventos 401/403 ativo.
- Deploy frontend com seletor de workspace e gestão OWNER/SUPER_ADMIN.
- Validar smoke:
  - login USER e SUPER_ADMIN;
  - troca de workspace;
  - OWNER inclui/remove GUEST;
  - GUEST bloqueado em `usuarios`;
  - workspace bloqueado nega acesso para USER.
- Acompanhar por 72h:
  - `counts_by_status` e `counts_by_type` em `/admin/security/summary`;
  - erros por `cross_workspace_denied`, `workspace_blocked`, `permission_denied`.

Critério de avanço para Release 2:

- sem incidente de vazamento entre workspaces;
- sem aumento anormal de 401/403 por erro sistêmico;
- sem regressão funcional crítica.

## 4. Release 2 (enforcement)

Objetivo: consolidar arquitetura definitiva por `workspace_id`.

Checklist técnico:

- aplicar migration para `workspace_id NOT NULL` nas tabelas de domínio.
- remover fallback de escopo legado (`user_id`).
- revalidar índices e constraints por workspace.
- reexecutar auditoria de plano de consulta (`EXPLAIN`).

Validação final:

- suíte de testes multiworkspace aprovada;
- smoke completo dos módulos (Dashboard, Contas, Lançamentos, Investimentos, Gerenciador, Importar CSV).

## 5. Monitoramento operacional

Durante a janela e nas 72h seguintes:

- coletar snapshot a cada 30 min:
  - `GET /admin/security/summary`
- registrar:
  - totais por status (`401`, `403`);
  - top eventos (`cross_workspace_denied`, `workspace_blocked`, `permission_denied`, `auth_invalid_token`);
  - volume por IP.

Sinais de alerta:

- salto de `401` após deploy (potencial regressão de token);
- salto de `403` em rotas core para OWNER;
- recorrência de `cross_workspace_denied` para usuários válidos.

## 6. Fallback / rollback

Se houver regressão crítica:

1. Reverter backend para commit anterior estável.
2. Reverter frontend para build anterior estável.
3. Manter dados intactos (sem rollback destrutivo de banco).
4. Comunicar usuários e congelar novas mudanças.
5. Abrir incidente com causa raiz e plano de correção.

## 7. Evidências de go-live

- hash do commit backend:
- hash do commit frontend:
- horário de início/fim da janela:
- responsável técnico:
- decisão final: `GO` / `ROLLBACK`
- links de evidência (logs, prints, relatório):
