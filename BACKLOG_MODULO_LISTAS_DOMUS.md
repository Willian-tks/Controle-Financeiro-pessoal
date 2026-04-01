# Backlog Técnico MVP - Módulo `Listas`

Data base: 2026-03-31
Atualizado em: 2026-04-01

## Painel de andamento

- [x] Fase 1 - Modelo de dados
- [x] Fase 2 - Schemas e contratos de API
- [x] Fase 3 - Repositório e consolidado
- [x] Fase 4 - Endpoints FastAPI
- [x] Fase 5 - Navegação e entrada do módulo no frontend
- [x] Fase 6 - Tela principal de listas
- [x] Fase 7 - Tela de detalhe da lista
- [x] Fase 8 - UX e consistência visual
- [ ] Fase 9 - Testes
- [ ] Fase 10 - Rollout controlado

## Conclusões já realizadas

- [x] Novo atalho `Listas` inserido no menu lateral abaixo de `Gerenciador`
- [x] Subtítulo inicial da página `Listas` adicionado no frontend
- [x] Tela placeholder inicial do módulo adicionada para navegação segura
- [x] Tabela `lists` criada em `db.py`
- [x] Tabela `list_items` criada em `db.py`
- [x] Índices `idx_lists_workspace`, `idx_lists_workspace_status`, `idx_lists_workspace_type` adicionados
- [x] Índices `idx_list_items_workspace` e `idx_list_items_workspace_list` adicionados
- [x] Estrutura preparada para SQLite e PostgreSQL
- [x] Migração automática encaixada no fluxo atual do backend
- [x] Teste automatizado da Fase 1 adicionado e validado
- [x] Schemas de listas e itens adicionados em `api/schemas.py`
- [x] Validações de nome, tipo, quantidade, valor sugerido e status adicionadas
- [x] Contratos de resposta com resumo consolidado adicionados
- [x] Teste automatizado da Fase 2 adicionado e validado
- [x] Repositório `lists_repo.py` criado
- [x] CRUD backend de listas implementado com `workspace_id`
- [x] CRUD backend de itens implementado com `workspace_id`
- [x] Consolidado por lista implementado no backend
- [x] Toggle de adquirido com `completion_date` implementado
- [x] Teste automatizado da Fase 3 adicionado e validado
- [x] Endpoints FastAPI de listas implementados em `api/main.py`
- [x] Endpoints FastAPI de itens implementados em `api/main.py`
- [x] Autenticação e escopo por workspace aplicados via contexto atual
- [x] Teste automatizado da Fase 4 adicionado e validado
- [x] Camada `frontend/src/api.js` integrada ao módulo `Listas`
- [x] Estado principal do módulo `Listas` criado em `frontend/src/App.jsx`
- [x] Tela principal com formulário, busca, filtros e cards implementada
- [x] Prévia de abertura da lista adicionada no frontend
- [x] Build do frontend validado após integração das Fases 5/6
- [x] CRUD de itens integrado ao frontend
- [x] Detalhe operacional da lista entregue na própria página `Listas`
- [x] Resumo da lista atualiza após mexer nos itens
- [x] Build do frontend validado após conclusão da Fase 7

## Próximas entregas imediatas

- [x] Refinar UX, estados vazios e feedbacks do módulo
- [x] Melhorar responsividade e acabamento visual do detalhe
- [x] Revisar textos e microinterações do módulo

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
5. O status da lista será apenas `ativa` ou `arquivada`.
6. O cálculo de item será sempre numérico:
   `valor_total = quantidade * valor_sugerido`
   se `valor_sugerido` não vier, considerar `0`
7. O backend deve devolver resumo consolidado da lista.
8. O item terá `sort_order` desde a V1.
9. O item terá `completion_date` persistido, mesmo sem destaque visual na primeira versão.

---

## Fase 1 - Modelo de dados

Status geral:
- [x] Concluída

### Objetivo
Criar as tabelas e campos necessários do módulo mantendo compatibilidade com a arquitetura atual do DOMUS.

### Entregáveis

- [x] tabela `lists`
- [x] tabela `list_items`
- [x] índices por `workspace_id`
- [x] estrutura pronta para SQLite e PostgreSQL

### Tarefas técnicas

- [x] Adicionar em `db.py` a tabela `lists`
- [x] Adicionar em `db.py` a tabela `list_items`
- [x] Criar índices:
  `idx_lists_workspace`
  `idx_lists_workspace_status`
  `idx_lists_workspace_type`
  `idx_list_items_workspace`
  `idx_list_items_workspace_list`
- [x] Garantir compatibilidade da migração em SQLite/Postgres

### Critérios de aceite

- [x] Aplicação sobe com as novas tabelas
- [x] Migração não quebra ambientes existentes
- [x] Leitura e escrita das tabelas funcionam em SQLite e PostgreSQL

### Observações da execução

- [x] Implementação feita em `db.py`
- [x] Cobertura inicial adicionada em `tests/test_lists_phase1_schema.py`

---

## Fase 2 - Schemas e contratos de API

Status geral:
- [x] Concluída

### Objetivo
Definir payloads e respostas do módulo de forma consistente com o padrão FastAPI do projeto.

### Entregáveis

- [x] request/response schemas de listas
- [x] request/response schemas de itens
- [x] estrutura de retorno com resumo consolidado

### Tarefas técnicas

- [x] Criar schemas em `api/schemas.py` para `ListCreateRequest`
- [x] Criar schemas em `api/schemas.py` para `ListUpdateRequest`
- [x] Criar schemas em `api/schemas.py` para `ListItemCreateRequest`
- [x] Criar schemas em `api/schemas.py` para `ListItemUpdateRequest`
- [x] Adicionar `ListToggleAcquiredRequest`
- [x] Definir validações:
  nome da lista obrigatório
  tipo obrigatório
  nome do item obrigatório
  quantidade > 0
  valor sugerido >= 0
  status aceito: `ativa`, `arquivada`
- [x] Padronizar estruturas de resposta para listagem de listas
- [x] Padronizar estruturas de resposta para detalhe da lista

### Critérios de aceite

- [x] Payload inválido retorna erro de validação com mensagem clara no contrato
- [x] Responses retornam dados coerentes com o consolidado

### Observações da execução

- [x] Implementação feita em `api/schemas.py`
- [x] Cobertura inicial adicionada em `tests/test_lists_phase2_schemas.py`

---

## Fase 3 - Repositório e consolidado

Status geral:
- [x] Concluída

### Objetivo
Implementar persistência e cálculos consolidados no backend.

### Entregáveis

- [x] repositório do módulo
- [x] funções de CRUD de listas
- [x] funções de CRUD de itens
- [x] cálculo consolidado por lista

### Tarefas técnicas

- [x] Criar `lists_repo.py` ou módulo equivalente seguindo o padrão atual
- [x] Implementar CRUD de listas com `workspace_id`
- [x] Implementar CRUD de itens com `workspace_id`
- [x] Garantir joins sempre na mesma partição lógica do workspace
- [x] Implementar cálculo consolidado:
  `total_items`
  `acquired_items`
  `pending_items`
  `completion_pct`
  `estimated_total`
- [x] Definir política para `sort_order`
  inicialmente usar ordem de criação
- [x] Ao marcar item como adquirido:
  `acquired = true`
  preencher `completion_date`
- [x] Ao desmarcar:
  `acquired = false`
  limpar `completion_date`

### Critérios de aceite

- [x] Toda consulta respeita `workspace_id`
- [x] Consolidado da lista fecha corretamente
- [x] Toggle de item atualiza estado e resumo

### Observações da execução

- [x] Implementação feita em `lists_repo.py`
- [x] Cobertura inicial adicionada em `tests/test_lists_phase3_repo.py`

---

## Fase 4 - Endpoints FastAPI

Status geral:
- [x] Concluída

### Objetivo
Expor o módulo por API interna do DOMUS.

### Entregáveis

- [x] endpoints de listas
- [x] endpoints de itens
- [x] proteção por autenticação e workspace

### Tarefas técnicas

- [x] Implementar `POST /lists`
- [x] Implementar `GET /lists`
- [x] Implementar `GET /lists/{id}`
- [x] Implementar `PUT /lists/{id}`
- [x] Implementar `DELETE /lists/{id}`
- [x] Implementar `PATCH /lists/{id}/archive`
- [x] Implementar `POST /lists/{id}/items`
- [x] Implementar `PUT /items/{id}`
- [x] Implementar `DELETE /items/{id}`
- [x] Implementar `PATCH /items/{id}/toggle-acquired`
- [x] Aplicar autenticação com usuário atual
- [x] Aplicar escopo por workspace
- [x] Padronizar mensagens de erro

### Critérios de aceite

- [x] Endpoints CRUD funcionando ponta a ponta
- [x] Acesso cross-workspace bloqueado
- [x] API entrega resumo consolidado nas consultas

### Observações da execução

- [x] Implementação feita em `api/main.py`
- [x] Cobertura inicial adicionada em `tests/test_lists_phase4_api.py`

---

## Fase 5 - Navegação e entrada do módulo no frontend

Status geral:
- [x] Concluída

### Objetivo
Adicionar o módulo à navegação principal e preparar estado de tela.

### Entregáveis

- [x] nova página `Listas`
- [x] entrada no menu
- [x] estado inicial funcional do módulo

### Tarefas técnicas

- [x] Adicionar `Listas` na navegação do frontend
- [x] Definir subtítulo da página
- [x] Criar tela inicial placeholder para navegação segura
- [x] Criar estado de frontend para:
  listas
  lista selecionada
  filtros
  busca
  itens
  mensagens e ações pendentes
- [x] Adicionar chamadas na camada `frontend/src/api.js`

### Critérios de aceite

- [x] Usuário consegue abrir a página `Listas`
- [x] Chamadas da API carregam sem quebrar a aplicação

### Observações da execução

- [x] Implementação feita em `frontend/src/api.js`
- [x] Implementação feita em `frontend/src/App.jsx`

---

## Fase 6 - Tela principal de listas

Status geral:
- [x] Concluída

### Objetivo
Entregar a visão principal do módulo com busca, filtros e cards.

### Entregáveis

- [x] tela principal de listas
- [x] botão `Nova Lista`
- [x] busca por nome
- [x] filtros por tipo e status
- [x] cards de listas com resumo

### Tarefas técnicas

- [x] Criar layout da página principal
- [x] Adicionar título
- [x] Adicionar botão `Nova Lista`
- [x] Adicionar busca
- [x] Adicionar filtro por tipo
- [x] Adicionar filtro por status
- [x] Renderizar cards das listas
- [x] Mostrar em cada card:
  nome
  tipo
  total de itens
  itens concluídos
  percentual de progresso
  valor total estimado
  status
- [x] Ações por card:
  abrir
  editar
  arquivar
  excluir

### Critérios de aceite

- [x] Usuário cria e enxerga listas na tela principal
- [x] Busca e filtros funcionam
- [x] Cards exibem resumo correto

### Observações da execução

- [x] A ação `abrir` foi entregue como prévia da lista no painel atual
- [x] O detalhe operacional completo permanece para a Fase 7

---

## Fase 7 - Tela de detalhe da lista

Status geral:
- [x] Concluída

### Objetivo
Entregar o uso operacional do módulo no detalhe da lista.

### Entregáveis

- [x] página de detalhe
- [x] resumo da lista
- [x] tabela de itens
- [x] ações por item

### Tarefas técnicas

- [x] Criar cabeçalho com nome
- [x] Criar cabeçalho com tipo
- [x] Criar cabeçalho com descrição
- [x] Criar cabeçalho com status
- [x] Criar bloco de resumo com:
  total de itens
  adquiridos
  pendentes
  percentual concluído
  valor total estimado
- [x] Criar tabela de itens com colunas:
  checkbox
  nome
  quantidade
  valor sugerido
  valor total
  observação
  ações
- [x] Ações por item:
  editar
  excluir
  marcar/desmarcar adquirido

### Critérios de aceite

- [x] Usuário opera a lista inteira sem sair da tela
- [x] Resumo atualiza ao mexer nos itens

### Observações da execução

- [x] O detalhe foi entregue dentro da própria página `Listas`, sem rota separada
- [x] Formulário de item, toggle e exclusão já conversam com a API do módulo

---

## Fase 8 - UX e consistência visual

Status geral:
- [x] Concluída

### Objetivo
Garantir aderência ao padrão visual e de uso do DOMUS.

### Entregáveis

- [x] visual consistente com o sistema
- [x] estados vazios
- [x] mensagens de feedback

### Tarefas técnicas

- [x] Aplicar padrão visual dos cards e tabelas do DOMUS
- [x] Adicionar estado vazio sem listas
- [x] Adicionar estado vazio sem itens
- [x] Adicionar feedback de sucesso e erro
- [x] Ajustar responsividade da tela principal e detalhe
- [x] Revisar textos e labels para linguagem simples

### Critérios de aceite

- [x] Módulo fica coerente com a experiência atual do DOMUS
- [x] Uso em desktop e mobile fica aceitável

### Observações da execução

- [x] Estados vazios da listagem e do detalhe foram refinados no frontend
- [x] Área de detalhe ganhou cabeçalho mais claro e indicador visual de status
- [x] Faixa de contexto com total de listas e filtros ativos foi adicionada
- [x] Ajustes responsivos foram aplicados para cards, resumo e ações
- [x] Build do frontend validado após os ajustes da Fase 8

---

## Fase 9 - Testes

Status geral:
- [ ] Parcial

### Objetivo
Cobrir backend e cenários principais do módulo.

### Entregáveis

- [x] testes de repositório
- [x] testes de API
- [ ] smoke test manual do frontend

### Tarefas técnicas

- [x] Testes de CRUD de listas
- [x] Testes de CRUD de itens
- [x] Testes de consolidado
- [x] Testes de toggle adquirido
- [x] Testes de isolamento por workspace
- [x] Testes de validação:
  quantidade inválida
  valor sugerido negativo
  nome obrigatório
- [ ] Smoke test manual:
  criar lista
  adicionar itens
  marcar item
  arquivar lista

### Critérios de aceite

- [x] Cenários felizes e erros principais cobertos
- [x] Sem vazamento cross-workspace

### Observações da execução

- [x] Teste de schema/migração inicial da Fase 1 já criado
- [x] Teste de schemas da Fase 2 já criado
- [x] Teste de repositório da Fase 3 já criado
- [x] Teste de API da Fase 4 já criado
- [x] Cobertura de repositório ampliada para update de lista, delete de item e recomputo do resumo
- [x] Cobertura de API ampliada para update/delete de listas e itens
- [x] Cobertura de validação ampliada para nome vazio, status inválido, quantidade inválida e valor negativo
- [x] Suíte completa do projeto validada com `python -m unittest discover -s tests -p "test_*.py" -v`

---

## Fase 10 - Rollout controlado

Status geral:
- [ ] Não iniciada

### Objetivo
Introduzir o módulo com baixo risco operacional.

### Entregáveis

- [ ] release controlado
- [ ] validação manual do fluxo
- [ ] documentação mínima

### Tarefas técnicas

- [ ] Validar módulo em ambiente local
- [ ] Fazer smoke no VPS após deploy
- [ ] Atualizar documentação técnica se necessário
- [ ] Confirmar que o módulo não impacta:
  dashboard
  lançamentos
  investimentos

### Critérios de aceite

- [ ] Módulo entra sem regressão visível nos módulos atuais

---

## Ordem recomendada de execução

- [x] 1. Fase 1 - Modelo de dados
- [x] 2. Fase 2 - Schemas
- [x] 3. Fase 3 - Repositório e consolidado
- [x] 4. Fase 4 - Endpoints
- [x] 5. Fase 5 - Navegação
- [x] 6. Fase 6 - Tela principal
- [x] 7. Fase 7 - Detalhe da lista
- [x] 8. Fase 8 - UX
- [ ] 9. Fase 9 - Testes
- [ ] 10. Fase 10 - Rollout

## Riscos principais

- [ ] Criar camada excessiva para um módulo pequeno e perder velocidade
- [ ] Misturar escopo por usuário com escopo por workspace
- [ ] Deixar cálculo consolidado no frontend e gerar divergência
- [ ] Expandir demais o escopo da V1 com funcionalidades futuras

## Recomendações finais

- [x] Implementar primeiro o básico e entregar valor rápido
- [x] Deixar integração financeira apenas preparada, não ativa na V1
- [x] Tratar `Listas` como módulo operacional simples, não como módulo de metas complexas ainda
- [x] Priorizar clareza de uso e baixo risco de regressão no produto atual
