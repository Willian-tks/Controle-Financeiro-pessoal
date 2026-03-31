# Checklist de Implementação - Módulo `Listas`

## Preparação
- [ ] Validar escopo final da V1
- [ ] Confirmar uso exclusivo de `workspace_id`
- [ ] Confirmar que integração financeira fica fora da V1
- [ ] Confirmar nomenclatura final do módulo: `Listas`

## Banco de Dados
- [ ] Criar tabela `lists`
- [ ] Criar tabela `list_items`
- [ ] Adicionar `workspace_id` nas novas tabelas
- [ ] Adicionar campo `status` em `lists`
- [ ] Adicionar campo `sort_order` em `list_items`
- [ ] Adicionar campo `completion_date` em `list_items`
- [ ] Adicionar índices por `workspace_id`
- [ ] Adicionar índice por `workspace_id + list_id`
- [ ] Validar migração em SQLite
- [ ] Validar migração em PostgreSQL

## Schemas e Validações
- [ ] Criar schema de criação de lista
- [ ] Criar schema de edição de lista
- [ ] Criar schema de criação de item
- [ ] Criar schema de edição de item
- [ ] Validar nome da lista obrigatório
- [ ] Validar tipo obrigatório
- [ ] Validar nome do item obrigatório
- [ ] Validar quantidade maior que zero
- [ ] Validar valor sugerido maior ou igual a zero
- [ ] Validar status permitido: `ativa`, `arquivada`

## Repositório
- [ ] Criar repositório do módulo
- [ ] Implementar criação de lista
- [ ] Implementar edição de lista
- [ ] Implementar exclusão de lista
- [ ] Implementar arquivamento de lista
- [ ] Implementar listagem de listas
- [ ] Implementar busca de lista por id
- [ ] Implementar criação de item
- [ ] Implementar edição de item
- [ ] Implementar exclusão de item
- [ ] Implementar toggle de adquirido
- [ ] Garantir filtro por `workspace_id` em todas as queries

## Regras de Negócio
- [ ] Calcular `total_value = quantity * suggested_value`
- [ ] Tratar `suggested_value` ausente como `0`
- [ ] Calcular `total_items`
- [ ] Calcular `acquired_items`
- [ ] Calcular `pending_items`
- [ ] Calcular `completion_pct`
- [ ] Calcular `estimated_total`
- [ ] Preencher `completion_date` ao marcar item
- [ ] Limpar `completion_date` ao desmarcar item
- [ ] Garantir ordenação inicial por `sort_order`/criação

## API
- [ ] Criar `POST /lists`
- [ ] Criar `GET /lists`
- [ ] Criar `GET /lists/{id}`
- [ ] Criar `PUT /lists/{id}`
- [ ] Criar `DELETE /lists/{id}`
- [ ] Criar `PATCH /lists/{id}/archive`
- [ ] Criar `POST /lists/{id}/items`
- [ ] Criar `PUT /items/{id}`
- [ ] Criar `DELETE /items/{id}`
- [ ] Criar `PATCH /items/{id}/toggle-acquired`
- [ ] Retornar resumo consolidado no `GET /lists`
- [ ] Retornar lista + itens + resumo no `GET /lists/{id}`
- [ ] Validar isolamento por workspace nas rotas

## Frontend - Base
- [ ] Adicionar módulo `Listas` na navegação
- [ ] Adicionar subtítulo da página
- [ ] Criar integrações em `frontend/src/api.js`
- [ ] Criar estados de listas
- [ ] Criar estados de itens
- [ ] Criar estados de filtros e busca
- [ ] Criar estados de loading e mensagens

## Frontend - Tela Principal
- [ ] Criar página principal `Listas`
- [ ] Adicionar botão `Nova Lista`
- [ ] Adicionar campo de busca
- [ ] Adicionar filtro por tipo
- [ ] Adicionar filtro por status
- [ ] Renderizar cards de listas
- [ ] Exibir nome da lista
- [ ] Exibir tipo
- [ ] Exibir total de itens
- [ ] Exibir itens concluídos
- [ ] Exibir percentual de progresso
- [ ] Exibir valor total estimado
- [ ] Exibir status
- [ ] Adicionar ação `abrir`
- [ ] Adicionar ação `editar`
- [ ] Adicionar ação `arquivar`
- [ ] Adicionar ação `excluir`

## Frontend - Detalhe da Lista
- [ ] Criar página de detalhe
- [ ] Exibir nome da lista
- [ ] Exibir tipo
- [ ] Exibir descrição
- [ ] Exibir status
- [ ] Exibir resumo consolidado
- [ ] Criar tabela de itens
- [ ] Adicionar checkbox de adquirido
- [ ] Exibir nome do item
- [ ] Exibir quantidade
- [ ] Exibir valor sugerido
- [ ] Exibir valor total
- [ ] Exibir observação
- [ ] Adicionar ação de editar item
- [ ] Adicionar ação de excluir item
- [ ] Adicionar ação de marcar/desmarcar adquirido

## UX e Visual
- [ ] Seguir padrão visual atual do DOMUS
- [ ] Ajustar cards para desktop e mobile
- [ ] Criar estado vazio sem listas
- [ ] Criar estado vazio sem itens
- [ ] Padronizar textos e labels
- [ ] Padronizar mensagens de sucesso
- [ ] Padronizar mensagens de erro

## Testes
- [ ] Testar criação de lista
- [ ] Testar edição de lista
- [ ] Testar exclusão de lista
- [ ] Testar arquivamento de lista
- [ ] Testar criação de item
- [ ] Testar edição de item
- [ ] Testar exclusão de item
- [ ] Testar toggle de adquirido
- [ ] Testar cálculo de `total_value`
- [ ] Testar cálculo de consolidado
- [ ] Testar lista sem itens
- [ ] Testar isolamento por workspace
- [ ] Testar payload inválido na API
- [ ] Rodar smoke test manual no frontend

## Deploy e Validação Final
- [ ] Validar localmente
- [ ] Rodar build do frontend
- [ ] Rodar testes automatizados
- [ ] Revisar impacto no VPS
- [ ] Publicar no Git
- [ ] Fazer deploy no VPS
- [ ] Validar módulo no ambiente publicado
- [ ] Confirmar que não houve regressão em outros módulos
