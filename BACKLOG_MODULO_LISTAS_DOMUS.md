# Backlog Técnico MVP - Módulo `Listas`

Data base: 2026-03-31

## 1. Objetivo do MVP

Implementar no DOMUS um novo módulo chamado `Listas`, com foco em organização pessoal simples e prática.

O MVP deve permitir:

1. Criar listas
2. Editar listas
3. Excluir listas
4. Arquivar listas
5. Listar listas com busca e filtros
6. Abrir detalhe de uma lista
7. Adicionar itens
8. Editar itens
9. Excluir itens
10. Marcar e desmarcar item como adquirido
11. Calcular total estimado e progresso

## 2. Decisões fechadas (travadas)

1. O módulo se chama `Listas`.
2. O escopo de dados será por `workspace_id`.
3. A primeira versão não terá integração automática com financeiro.
4. A primeira versão não terá recorrência, modelos ou valor real pago.
5. O status da lista será apenas:
   - `ativa`
   - `arquivada`
6. O cálculo de item será sempre numérico:
   - `valor_total = quantidade * valor_sugerido`
   - se `valor_sugerido` não vier, considerar `0`
7. O backend deve devolver resumo consolidado da lista.
8. O item terá `sort_order` desde a V1.
9. O item terá `completion_date` persistido, mesmo sem destaque visual na primeira versão.

---

## Fase 1 - Modelo de dados

### Objetivo
Criar as tabelas e campos necessários do módulo mantendo compatibilidade com a arquitetura atual do DOMUS.

### Entregáveis

- tabela `lists`
- tabela `list_items`
- índices por `workspace_id`
- estrutura pronta para SQLite e PostgreSQL

### Tarefas técnicas

- [ ] Adicionar em `db.py` a tabela `lists` com:
  - `id`
  - `workspace_id`
  - `name`
  - `type`
  - `description`
  - `status`
  - `created_at`
  - `updated_at`
- [ ] Adicionar em `db.py` a tabela `list_items` com:
  - `id`
  - `workspace_id`
  - `list_id`
  - `name`
  - `quantity`
  - `suggested_value`
  - `total_value`
  - `acquired`
  - `completion_date`
  - `notes`
  - `sort_order`
  - `created_at`
  - `updated_at`
- [ ] Criar índices:
  - `idx_lists_workspace`
  - `idx_lists_workspace_status`
  - `idx_lists_workspace_type`
  - `idx_list_items_workspace`
  - `idx_list_items_workspace_list`
- [ ] Garantir compatibilidade da migração em SQLite/Postgres

### Critérios de aceite

- [ ] Aplicação sobe com as novas tabelas
- [ ] Migração não quebra ambientes existentes
- [ ] Leitura e escrita das tabelas funcionam em SQLite e PostgreSQL

---

## Fase 2 - Schemas e contratos de API

### Objetivo
Definir payloads e respostas do módulo de forma consistente com o padrão FastAPI do projeto.

### Entregáveis

- request/response schemas de listas
- request/response schemas de itens
- estrutura de retorno com resumo consolidado

### Tarefas técnicas

- [ ] Criar schemas em `api/schemas.py` para:
  - `ListCreateRequest`
  - `ListUpdateRequest`
  - `ListItemCreateRequest`
  - `ListItemUpdateRequest`
  - `ListToggleAcquiredRequest` se necessário
- [ ] Definir validações:
  - nome da lista obrigatório
  - tipo obrigatório
  - nome do item obrigatório
  - quantidade > 0
  - valor sugerido >= 0
  - status aceito: `ativa`, `arquivada`
- [ ] Padronizar estruturas de resposta para:
  - listagem de listas
  - detalhe da lista

### Critérios de aceite

- [ ] Payload inválido retorna `400` com mensagem clara
- [ ] Responses retornam dados coerentes com o consolidado

---

## Fase 3 - Repositório e consolidado

### Objetivo
Implementar persistência e cálculos consolidados no backend.

### Entregáveis

- repositório do módulo
- funções de CRUD de listas
- funções de CRUD de itens
- cálculo consolidado por lista

### Tarefas técnicas

- [ ] Criar `lists_repo.py` ou módulo equivalente seguindo o padrão atual
- [ ] Implementar CRUD de listas com `workspace_id`
- [ ] Implementar CRUD de itens com `workspace_id`
- [ ] Garantir joins sempre na mesma partição lógica do workspace
- [ ] Implementar cálculo consolidado:
  - `total_items`
  - `acquired_items`
  - `pending_items`
  - `completion_pct`
  - `estimated_total`
- [ ] Definir política para `sort_order`
  - inicialmente usar ordem de criação
- [ ] Ao marcar item como adquirido:
  - `acquired = true`
  - preencher `completion_date`
- [ ] Ao desmarcar:
  - `acquired = false`
  - limpar `completion_date`

### Critérios de aceite

- [ ] Toda consulta respeita `workspace_id`
- [ ] Consolidado da lista fecha corretamente
- [ ] Toggle de item atualiza estado e resumo

---

## Fase 4 - Endpoints FastAPI

### Objetivo
Expor o módulo por API interna do DOMUS.

### Entregáveis

- endpoints de listas
- endpoints de itens
- proteção por autenticação e workspace

### Tarefas técnicas

- [ ] Implementar rotas em `api/main.py`:
  - `POST /lists`
  - `GET /lists`
  - `GET /lists/{id}`
  - `PUT /lists/{id}`
  - `DELETE /lists/{id}`
  - `PATCH /lists/{id}/archive`
  - `POST /lists/{id}/items`
  - `PUT /items/{id}`
  - `DELETE /items/{id}`
  - `PATCH /items/{id}/toggle-acquired`
- [ ] Aplicar autenticação com usuário atual
- [ ] Aplicar escopo por workspace
- [ ] Padronizar mensagens de erro

### Critérios de aceite

- [ ] Endpoints CRUD funcionando ponta a ponta
- [ ] Acesso cross-workspace bloqueado
- [ ] API entrega resumo consolidado nas consultas

---

## Fase 5 - Navegação e entrada do módulo no frontend

### Objetivo
Adicionar o módulo à navegação principal e preparar estado de tela.

### Entregáveis

- nova página `Listas`
- entrada no menu
- estado inicial do módulo

### Tarefas técnicas

- [ ] Adicionar `Listas` na navegação do frontend
- [ ] Definir subtítulo da página
- [ ] Criar estado de frontend para:
  - listas
  - lista selecionada
  - filtros
  - busca
  - itens
  - mensagens e ações pendentes
- [ ] Adicionar chamadas na camada `frontend/src/api.js`

### Critérios de aceite

- [ ] Usuário consegue abrir a página `Listas`
- [ ] Chamadas da API carregam sem quebrar a aplicação

---

## Fase 6 - Tela principal de listas

### Objetivo
Entregar a visão principal do módulo com busca, filtros e cards.

### Entregáveis

- tela principal de listas
- botão `Nova Lista`
- busca por nome
- filtros por tipo e status
- cards de listas com resumo

### Tarefas técnicas

- [ ] Criar layout da página principal
- [ ] Adicionar:
  - título
  - botão `Nova Lista`
  - busca
  - filtro por tipo
  - filtro por status
- [ ] Renderizar cards das listas
- [ ] Mostrar em cada card:
  - nome
  - tipo
  - total de itens
  - itens concluídos
  - percentual de progresso
  - valor total estimado
  - status
- [ ] Ações por card:
  - abrir
  - editar
  - arquivar
  - excluir

### Critérios de aceite

- [ ] Usuário cria e enxerga listas na tela principal
- [ ] Busca e filtros funcionam
- [ ] Cards exibem resumo correto

---

## Fase 7 - Tela de detalhe da lista

### Objetivo
Entregar o uso operacional do módulo no detalhe da lista.

### Entregáveis

- página de detalhe
- resumo da lista
- tabela de itens
- ações por item

### Tarefas técnicas

- [ ] Criar cabeçalho com:
  - nome
  - tipo
  - descrição
  - status
- [ ] Criar bloco de resumo com:
  - total de itens
  - adquiridos
  - pendentes
  - percentual concluído
  - valor total estimado
- [ ] Criar tabela de itens com colunas:
  - checkbox
  - nome
  - quantidade
  - valor sugerido
  - valor total
  - observação
  - ações
- [ ] Ações por item:
  - editar
  - excluir
  - marcar/desmarcar adquirido

### Critérios de aceite

- [ ] Usuário opera a lista inteira sem sair da tela
- [ ] Resumo atualiza ao mexer nos itens

---

## Fase 8 - UX e consistência visual

### Objetivo
Garantir aderência ao padrão visual e de uso do DOMUS.

### Entregáveis

- visual consistente com o sistema
- estados vazios
- mensagens de feedback

### Tarefas técnicas

- [ ] Aplicar padrão visual dos cards e tabelas do DOMUS
- [ ] Adicionar estados vazios:
  - sem listas
  - sem itens
- [ ] Adicionar feedback de sucesso e erro
- [ ] Ajustar responsividade da tela principal e detalhe
- [ ] Revisar textos e labels para linguagem simples

### Critérios de aceite

- [ ] Módulo fica coerente com a experiência atual do DOMUS
- [ ] Uso em desktop e mobile fica aceitável

---

## Fase 9 - Testes

### Objetivo
Cobrir backend e cenários principais do módulo.

### Entregáveis

- testes de repositório
- testes de API
- smoke test manual do frontend

### Tarefas técnicas

- [ ] Testes de CRUD de listas
- [ ] Testes de CRUD de itens
- [ ] Testes de consolidado
- [ ] Testes de toggle adquirido
- [ ] Testes de isolamento por workspace
- [ ] Testes de validação:
  - quantidade inválida
  - valor sugerido negativo
  - nome obrigatório
- [ ] Smoke test manual:
  - criar lista
  - adicionar itens
  - marcar item
  - arquivar lista

### Critérios de aceite

- [ ] Cenários felizes e erros principais cobertos
- [ ] Sem vazamento cross-workspace

---

## Fase 10 - Rollout controlado

### Objetivo
Introduzir o módulo com baixo risco operacional.

### Entregáveis

- release controlado
- validação manual do fluxo
- documentação mínima

### Tarefas técnicas

- [ ] Validar módulo em ambiente local
- [ ] Fazer smoke no VPS após deploy
- [ ] Atualizar documentação técnica se necessário
- [ ] Confirmar que o módulo não impacta:
  - dashboard
  - lançamentos
  - investimentos

### Critérios de aceite

- [ ] Módulo entra sem regressão visível nos módulos atuais

---

## Ordem recomendada de execução

1. Fase 1 - Modelo de dados
2. Fase 2 - Schemas
3. Fase 3 - Repositório e consolidado
4. Fase 4 - Endpoints
5. Fase 5 - Navegação
6. Fase 6 - Tela principal
7. Fase 7 - Detalhe da lista
8. Fase 8 - UX
9. Fase 9 - Testes
10. Fase 10 - Rollout

## Riscos principais

1. Criar camada excessiva para um módulo pequeno e perder velocidade.
2. Misturar escopo por usuário com escopo por workspace.
3. Deixar cálculo consolidado no frontend e gerar divergência.
4. Expandir demais o escopo da V1 com funcionalidades futuras.

## Recomendações finais

1. Implementar primeiro o básico e entregar valor rápido.
2. Deixar integração financeira apenas preparada, não ativa na V1.
3. Tratar `Listas` como módulo operacional simples, não como módulo de metas complexas ainda.
4. Priorizar clareza de uso e baixo risco de regressão no produto atual.
