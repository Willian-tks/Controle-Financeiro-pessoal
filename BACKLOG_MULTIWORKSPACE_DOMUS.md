# DOMUS - Backlog Tecnico Multi-Workspace
## Arquitetura SaaS Multi-Tenant com `workspace_id`

Data base: 2026-03-04

## 1. Objetivo

Implementar arquitetura multi-tenant em banco unico com isolamento por `workspace_id`, mantendo:

- Hierarquia global de usuarios (`SUPER_ADMIN`, `USER`)
- Hierarquia por workspace (`OWNER`, `GUEST`)
- Permissoes granulares por modulo
- Bloqueio de workspace
- Escalabilidade e governanca para SaaS

## 2. Contexto atual (base existente)

O sistema hoje ja opera com escopo por `user_id` em:

- Schema/migracoes: `db.py`
- Autenticacao/token: `auth.py`, `api/security.py`, `api/main.py`
- Repositorios: `repo.py`, `invest_repo.py`
- Relatorios: `reports.py`

Esse backlog transforma o escopo principal de `user_id` para `workspace_id` com rollout controlado (sem "big bang").

## 3. Decisoes de arquitetura (travadas)

1. Banco unico com isolamento logico por `workspace_id`.
2. `SUPER_ADMIN` e papel global (fora da hierarquia interna do workspace).
3. `OWNER` e `GUEST` sao papeis por workspace (tabela de associacao).
4. Workspace bloqueado impede acesso de `OWNER/GUEST` e mantem acesso administrativo de `SUPER_ADMIN`.
5. Rollout em duas etapas:
   - Etapa 1: dual-read/dual-write com compatibilidade.
   - Etapa 2: consolidacao total em `workspace_id`.

## 4. Mapeamento de modulos para permissao

Modulos controlados:

- `dashboard`
- `lancamentos`
- `investimentos`
- `relatorios`
- `contas`
- `usuarios`

Regras fixas:

- `SUPER_ADMIN`: bypass de permissao interna.
- `OWNER`: permissao total no workspace.
- `GUEST`: matriz da tabela `permissions`.
- `GUEST` nunca acessa modulo `usuarios`.

---

## Fase A - Fundacao de schema e compatibilidade

### Objetivo
Criar estruturas de workspace sem quebrar funcionamento atual.

### Entregaveis

- [x] Nova tabela `workspaces`
- [x] Nova tabela `workspace_users`
- [x] Nova tabela `permissions`
- [x] Coluna `workspace_id` em todas as tabelas de dominio
- [x] Indices por `workspace_id`

### Tarefas tecnicas

- [x] `db.py`: adicionar `CREATE TABLE`/migracao para:
  - `workspaces(id, name, owner_user_id, status, created_at)`
  - `workspace_users(id, workspace_id, user_id, role, created_by, created_at)`
  - `permissions(id, workspace_user_id, module, can_view, can_add, can_edit, can_delete)`
- [x] `db.py`: adicionar `workspace_id` em:
  - `accounts`, `categories`, `transactions`
  - `assets`, `trades`, `income_events`, `prices`, `asset_prices`, `index_rates`
  - `credit_cards`, `credit_card_invoices`, `credit_card_charges`
- [x] `db.py`: criar indices:
  - `idx_*_workspace` por tabela
  - compostos criticos de unicidade por workspace (ex.: nome conta, nome categoria, simbolo ativo)
- [x] `db.py`: manter compatibilidade durante migracao (sem `NOT NULL` imediato em etapa inicial)

### Critérios de aceite

- [x] Migracao executa sem perda de dados.
- [x] Aplicacao sobe com schema novo.
- [x] Nenhuma consulta quebra por coluna ausente.

---

## Fase B - Backfill e bootstrap de workspaces

### Objetivo
Popular `workspace_id` para dados legados de forma segura.

### Entregaveis

- [x] Workspace pessoal por usuario existente
- [x] Vinculo `OWNER` em `workspace_users`
- [x] Backfill de `workspace_id` em todas as tabelas de dominio

### Tarefas tecnicas

- [x] `db.py`/script dedicado: criar um workspace "Pessoal - <email>" para cada `users.id`.
- [x] Script de backfill:
  - `workspace_id` por `user_id` em todas as tabelas de dominio.
- [x] Criar `workspace_users` com `role='OWNER'` para cada workspace criado.
- [x] Validar orfaos e gerar relatorio de inconsistencias antes de travar `NOT NULL`.

### Critérios de aceite

- [x] 100% das linhas de dominio com `workspace_id` preenchido.
- [x] Cada usuario possui ao menos 1 workspace valido.
- [x] Sem dados sem dono logico.

---

## Fase C - Contexto de workspace e middleware de isolamento

### Objetivo
Forcar escopo de acesso por workspace em runtime.

### Entregaveis

- [x] Contexto de workspace ativo no request
- [x] Middleware de isolamento por workspace
- [x] Middleware de bloqueio por status do workspace

### Tarefas tecnicas

- [x] Criar `workspace_tenant.py` (ou evoluir `tenant.py`) para carregar:
  - `current_user_id`
  - `current_workspace_id`
  - `current_workspace_role`
- [x] `api/security.py`: incluir `workspace_id` no token.
- [x] `api/main.py`: extrair `workspace_id` do token/header e validar associacao em `workspace_users`.
- [x] `api/main.py`: negar acesso se `workspaces.status != 'active'` para nao admin.

### Critérios de aceite

- [x] Usuario fora do workspace recebe `403`.
- [x] Workspace bloqueado impede acesso de OWNER/GUEST.
- [x] SUPER_ADMIN mantem acesso administrativo.

---

## Fase D - Modelo de papeis (global e por workspace)

### Objetivo
Separar papel global de papel do workspace.

### Entregaveis

- [x] `users.global_role` consolidado
- [x] `workspace_users.role` ativo (`OWNER`/`GUEST`)

### Tarefas tecnicas

- [x] Migrar `users.role` para `users.global_role` com compatibilidade.
- [x] Ajustar `auth.py` para leitura/escrita de `global_role`.
- [ ] Ajustar endpoints administrativos em `api/main.py`:
  - criar OWNER (com workspace)
  - criar GUEST (em workspace existente)
  - promover SUPER_ADMIN (restrito a SUPER_ADMIN)

### Critérios de aceite

- [x] Nao existe ambiguidade entre role global e role local.
- [x] OWNER/GUEST funcionam apenas dentro do workspace.

---

## Fase E - Refactor dos repositorios para `workspace_id`

### Objetivo
Migrar regra de escopo de dados para `workspace_id`.

### Entregaveis

- [ ] Repositorio transacional (`repo.py`) filtrando por `workspace_id`
- [ ] Repositorio de investimentos (`invest_repo.py`) filtrando por `workspace_id`
- [ ] Relatorios (`reports.py`) filtrando por `workspace_id`

### Tarefas tecnicas

- [ ] Substituir `_uid(...)` por helper de escopo (ex.: `_scope_workspace_id(...)`).
- [ ] Atualizar todas as queries para `WHERE workspace_id = ?`.
- [ ] Atualizar joins garantindo mesma particao (`t.workspace_id = a.workspace_id`, etc).
- [ ] Revisar constraints unicas para chave por workspace.

### Critérios de aceite

- [ ] Nao ha query de dominio sem filtro por workspace.
- [ ] Teste de isolamento nao encontra vazamento cross-workspace.

---

## Fase F - Permissoes granulares por modulo

### Objetivo
Aplicar controle de acao por modulo para `GUEST`.

### Entregaveis

- [ ] Middleware/servico `check_permission(module, action)`
- [ ] Seeds de permissao default por novo GUEST
- [ ] Protecao de rotas por modulo/acao

### Tarefas tecnicas

- [ ] Criar servico de permissao (ex.: `permissions_service.py`).
- [ ] Mapear rotas FastAPI para modulo/acao.
- [ ] Bloquear acesso de `GUEST` ao modulo `usuarios`.
- [ ] Criar endpoints para OWNER editar permissoes de GUEST.

### Critérios de aceite

- [ ] GUEST sem permissao recebe `403`.
- [ ] OWNER sempre tem acesso total no workspace.
- [ ] SUPER_ADMIN ignora regras internas.

---

## Fase G - Interface de gestao de usuarios/workspace

### Objetivo
Disponibilizar governanca pelo frontend.

### Entregaveis

- [ ] Tela OWNER para convidados e permissoes
- [ ] Tela SUPER_ADMIN para criacao de OWNER e bloqueio de workspace
- [ ] Seletor de workspace ativo (quando usuario tiver mais de 1)

### Tarefas tecnicas

- [ ] `frontend/src/App.jsx`: pagina de gestao de usuarios/workspaces.
- [ ] `frontend/src/api.js`: endpoints de workspace, membros e permissoes.
- [ ] Fluxo de troca de workspace e refresh de contexto/token.

### Critérios de aceite

- [ ] OWNER gerencia GUEST sem acesso a recursos globais.
- [ ] SUPER_ADMIN gerencia workspaces e bloqueios.
- [ ] Troca de workspace atualiza dados sem vazamento.

---

## Fase H - Testes, observabilidade e rollout

### Objetivo
Entrar em producao com seguranca.

### Entregaveis

- [ ] Suite de testes de isolamento/permissao/bloqueio
- [ ] Check de performance por indices e plano de consulta
- [ ] Plano de rollout com fallback

### Tarefas tecnicas

- [ ] Criar testes automatizados:
  - isolamento A vs B
  - GUEST sem edit/delete
  - bloqueio de workspace no login e nas rotas
  - OWNER full dentro do workspace
  - SUPER_ADMIN com bypass
- [ ] Auditar queries com `EXPLAIN` em pontos criticos.
- [ ] Monitorar erros `403/401` e tentativas cross-workspace.
- [ ] Definir cutover:
  - release 1: dual mode
  - release 2: enforce `workspace_id NOT NULL` + remoção de fallback

### Critérios de aceite

- [ ] Testes obrigatorios passando.
- [ ] Sem regressao funcional nos modulos atuais.
- [ ] Sem vazamento entre workspaces em homologacao.

---

## 5. Ordem recomendada de implementacao

1. Fase A (schema)
2. Fase B (backfill)
3. Fase C (middleware isolamento + bloqueio)
4. Fase D (modelo de papeis)
5. Fase E (refactor repositorios)
6. Fase F (permissoes granulares)
7. Fase G (frontend de gestao)
8. Fase H (testes/rollout)

---

## 6. Definition of Done (DoD) do projeto

- [ ] Todas as tabelas de dominio com `workspace_id` e indice.
- [ ] 100% das rotas protegidas por escopo de workspace.
- [ ] 100% das queries de dominio com filtro por workspace.
- [ ] Papel global separado de papel por workspace.
- [ ] Permissoes granulares ativas para GUEST.
- [ ] Bloqueio de workspace aplicado em login e uso.
- [ ] Suite de seguranca/permissao/isolamento passando.

---

## 7. Backlog de execucao imediata (proxima sprint)

- [x] Sprint 1: Fase A + Fase B (schema/backfill)
- [ ] Sprint 2: Fase C + Fase D (auth/contexto/papeis)
- [ ] Sprint 3: Fase E + Fase F (repos/permissoes)
- [ ] Sprint 4: Fase G + Fase H (ui/testes/rollout)
