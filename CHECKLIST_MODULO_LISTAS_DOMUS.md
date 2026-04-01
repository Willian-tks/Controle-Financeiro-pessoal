# Checklist de Implementação - Módulo `Listas`

## Preparação
- [x] Validar escopo final da V1
- [x] Confirmar uso exclusivo de `workspace_id`
- [x] Confirmar que integração financeira fica fora da V1
- [x] Confirmar nomenclatura final do módulo: `Listas`

## Banco de Dados
- [x] Criar tabela `lists`
- [x] Criar tabela `list_items`
- [x] Adicionar `workspace_id` nas novas tabelas
- [x] Adicionar campo `status` em `lists`
- [x] Adicionar campo `sort_order` em `list_items`
- [x] Adicionar campo `completion_date` em `list_items`
- [x] Adicionar índices por `workspace_id`
- [x] Adicionar índice por `workspace_id + list_id`
- [x] Validar migração em SQLite
- [ ] Validar migração em PostgreSQL

## Schemas e Validações
- [x] Criar schema de criação de lista
- [x] Criar schema de edição de lista
- [x] Criar schema de criação de item
- [x] Criar schema de edição de item
- [x] Validar nome da lista obrigatório
- [x] Validar tipo obrigatório
- [x] Validar nome do item obrigatório
- [x] Validar quantidade maior que zero
- [x] Validar valor sugerido maior ou igual a zero
- [x] Validar status permitido: `ativa`, `arquivada`

## Repositório
- [x] Criar repositório do módulo
- [x] Implementar criação de lista
- [x] Implementar edição de lista
- [x] Implementar exclusão de lista
- [x] Implementar arquivamento de lista
- [x] Implementar listagem de listas
- [x] Implementar busca de lista por id
- [x] Implementar criação de item
- [x] Implementar edição de item
- [x] Implementar exclusão de item
- [x] Implementar toggle de adquirido
- [x] Garantir filtro por `workspace_id` em todas as queries

## Regras de Negócio
- [x] Calcular `total_value = quantity * suggested_value`
- [x] Tratar `suggested_value` ausente como `0`
- [x] Calcular `total_items`
- [x] Calcular `acquired_items`
- [x] Calcular `pending_items`
- [x] Calcular `completion_pct`
- [x] Calcular `estimated_total`
- [x] Preencher `completion_date` ao marcar item
- [x] Limpar `completion_date` ao desmarcar item
- [x] Garantir ordenação inicial por `sort_order`/criação

## API
- [x] Criar `POST /lists`
- [x] Criar `GET /lists`
- [x] Criar `GET /lists/{id}`
- [x] Criar `PUT /lists/{id}`
- [x] Criar `DELETE /lists/{id}`
- [x] Criar `PATCH /lists/{id}/archive`
- [x] Criar `POST /lists/{id}/items`
- [x] Criar `PUT /items/{id}`
- [x] Criar `DELETE /items/{id}`
- [x] Criar `PATCH /items/{id}/toggle-acquired`
- [x] Retornar resumo consolidado no `GET /lists`
- [x] Retornar lista + itens + resumo no `GET /lists/{id}`
- [x] Validar isolamento por workspace nas rotas

## Frontend - Base
- [x] Adicionar módulo `Listas` na navegação
- [x] Adicionar subtítulo da página
- [x] Criar integrações em `frontend/src/api.js`
- [x] Criar estados de listas
- [x] Criar estados de itens
- [x] Criar estados de filtros e busca
- [x] Criar estados de loading e mensagens

## Frontend - Tela Principal
- [x] Criar página principal `Listas`
- [x] Adicionar botão `Nova Lista`
- [x] Adicionar campo de busca
- [x] Adicionar filtro por tipo
- [x] Adicionar filtro por status
- [x] Renderizar cards de listas
- [x] Exibir nome da lista
- [x] Exibir tipo
- [x] Exibir total de itens
- [x] Exibir itens concluídos
- [x] Exibir percentual de progresso
- [x] Exibir valor total estimado
- [x] Exibir status
- [x] Adicionar ação `abrir`
- [x] Adicionar ação `editar`
- [x] Adicionar ação `arquivar`
- [x] Adicionar ação `excluir`

## Frontend - Detalhe da Lista
- [x] Criar página de detalhe
- [x] Exibir nome da lista
- [x] Exibir tipo
- [x] Exibir descrição
- [x] Exibir status
- [x] Exibir resumo consolidado
- [x] Criar tabela de itens
- [x] Adicionar checkbox de adquirido
- [x] Exibir nome do item
- [x] Exibir quantidade
- [x] Exibir valor sugerido
- [x] Exibir valor total
- [x] Exibir observação
- [x] Adicionar ação de editar item
- [x] Adicionar ação de excluir item
- [x] Adicionar ação de marcar/desmarcar adquirido

## UX e Visual
- [x] Seguir padrão visual atual do DOMUS
- [x] Ajustar cards para desktop e mobile
- [x] Criar estado vazio sem listas
- [x] Criar estado vazio sem itens
- [x] Padronizar textos e labels
- [x] Padronizar mensagens de sucesso
- [x] Padronizar mensagens de erro

## Testes
- [x] Testar criação de lista
- [x] Testar edição de lista
- [x] Testar exclusão de lista
- [x] Testar arquivamento de lista
- [x] Testar criação de item
- [x] Testar edição de item
- [x] Testar exclusão de item
- [x] Testar toggle de adquirido
- [x] Testar cálculo de `total_value`
- [x] Testar cálculo de consolidado
- [x] Testar lista sem itens
- [x] Testar isolamento por workspace
- [x] Testar payload inválido na API
- [ ] Rodar smoke test manual no frontend

## Deploy e Validação Final
- [x] Validar localmente
- [x] Rodar build do frontend
- [x] Rodar testes automatizados
- [x] Revisar impacto no VPS
- [ ] Publicar no Git
- [ ] Fazer deploy no VPS
- [ ] Validar módulo no ambiente publicado
- [ ] Confirmar que não houve regressão em outros módulos

## Gate antes de usuário real
- [ ] Executar smoke manual local do fluxo `Listas`
- [ ] Fazer deploy controlado no VPS
- [ ] Validar smoke pós-deploy no VPS
- [ ] Liberar para teste real de usuário somente após os itens acima
