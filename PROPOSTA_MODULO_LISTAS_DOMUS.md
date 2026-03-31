# Proposta de Implementação: Módulo `Listas`

## Objetivo
Criar no DOMUS um módulo simples de organização pessoal chamado `Listas`, com foco em planejamento prático do dia a dia.

O módulo deve permitir que o usuário:
- crie várias listas
- dê nome e tipo para cada lista
- adicione itens
- informe quantidade
- informe valor sugerido opcional
- acompanhe total estimado
- marque itens como adquiridos
- visualize progresso da lista

## Posicionamento no DOMUS
Este módulo deve nascer como uma funcionalidade de apoio à organização pessoal, sem competir com o núcleo financeiro do sistema.

A proposta para a primeira versão é:
- simples
- rápida de usar
- consistente com o visual do DOMUS
- preparada para futura integração com lançamentos financeiros

## Escopo aprovado para a V1

### Funcionalidades da lista
- criar lista
- editar lista
- excluir lista
- arquivar lista
- listar listas
- abrir detalhe da lista

### Funcionalidades dos itens
- adicionar item
- editar item
- excluir item
- marcar item como adquirido
- desmarcar item como adquirido

### Visões do módulo
- página principal de listas
- página de detalhe da lista

### Resumos e indicadores
- total de itens
- itens adquiridos
- itens pendentes
- percentual de conclusão
- valor total estimado

## Fora da V1
Os itens abaixo não entram na primeira entrega:
- duplicar lista
- orçamento previsto
- data alvo
- ícone customizado
- cor customizada
- prioridade
- link de referência
- valor real pago
- integração automática com financeiro
- modelos de lista
- listas recorrentes

## Ajustes recomendados para o DOMUS

### 1. Escopo por `workspace_id`
No DOMUS, o módulo deve usar `workspace_id` como padrão de escopo.

Não adotar `user_id ou workspace_id` como decisão em aberto.

Padrão recomendado:
- listas vinculadas ao workspace atual
- itens vinculados à lista do workspace atual
- consultas sempre respeitando o contexto multiworkspace já usado no sistema

### 2. Campo de ordenação
Mesmo sem drag and drop na V1, vale preparar a estrutura para ordenar itens.

Adicionar no item:
- `sort_order integer not null default 0`

Benefício:
- evita retrabalho futuro
- permite ordenar por criação inicialmente
- facilita evolução posterior

### 3. `valor_total` como cálculo consistente
Para simplificar backend e frontend, tratar `valor_total` como valor calculado sempre numérico.

Regra:
- se `valor_sugerido` não for informado, considerar `0`
- `valor_total = quantidade * valor_sugerido`

Benefício:
- menos tratamento de `null`
- somatórios mais simples
- UI mais previsível

### 4. Registrar `data_conclusao`
Mesmo que a data não apareça na interface da V1, ela deve ser persistida.

Regra:
- ao marcar item como adquirido: preencher `data_conclusao`
- ao desmarcar: limpar `data_conclusao`

Benefício:
- histórico pronto para futura evolução
- pode ser útil em relatórios depois

### 5. Camadas do projeto
Seguir o padrão atual do DOMUS, mas sem criar camadas artificiais.

Estrutura sugerida:
- schemas/DTOs
- repository
- router/controller
- componentes de UI
- página principal
- página de detalhe

Camada `service`:
- usar apenas se a regra de negócio justificar
- evitar service vazio só por formalidade

## Modelo funcional da V1

### Tipos de lista
Tipos sugeridos:
- Mercado
- Farmácia
- Casa
- Pessoal
- Desejos
- Outros

### Status de lista
Status aceitos:
- ativa
- arquivada

### Campos da lista
- `id`
- `workspace_id`
- `name`
- `type`
- `description` opcional
- `status`
- `created_at`
- `updated_at`

### Campos do item
- `id`
- `list_id`
- `name`
- `quantity`
- `suggested_value`
- `total_value`
- `acquired`
- `completion_date` opcional
- `notes` opcional
- `sort_order`
- `created_at`
- `updated_at`

## Regras de negócio

### Cálculo do item
- `total_value = quantity * suggested_value`
- se `suggested_value` não for informado, usar `0`

### Consolidado da lista
Cada lista deve retornar:
- `total_items`
- `acquired_items`
- `pending_items`
- `completion_pct`
- `estimated_total`

Fórmulas:
- `pending_items = total_items - acquired_items`
- `completion_pct = acquired_items / total_items * 100`
- `estimated_total = soma(total_value dos itens)`

Se a lista não tiver itens:
- `completion_pct = 0`

### Marcação do item
- ao marcar adquirido: `acquired = true` e preencher `completion_date`
- ao desmarcar: `acquired = false` e limpar `completion_date`

### Validações
- nome da lista obrigatório
- tipo obrigatório
- nome do item obrigatório
- quantidade maior que zero
- valor sugerido maior ou igual a zero

## Estrutura técnica sugerida

### Banco
Tabela `lists`
- `id`
- `workspace_id`
- `name`
- `type`
- `description`
- `status`
- `created_at`
- `updated_at`

Tabela `list_items`
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

### Índices sugeridos
- índice por `workspace_id` em `lists`
- índice por `workspace_id, list_id` em `list_items`
- índice por `workspace_id, status` em `lists`
- índice por `workspace_id, type` em `lists`

## API recomendada

### Listas
- `POST /lists`
- `GET /lists`
- `GET /lists/{id}`
- `PUT /lists/{id}`
- `DELETE /lists/{id}`
- `PATCH /lists/{id}/archive`

### Itens
- `POST /lists/{id}/items`
- `PUT /items/{id}`
- `DELETE /items/{id}`
- `PATCH /items/{id}/toggle-acquired`

## Respostas esperadas

### `GET /lists`
Cada lista deve retornar:
- dados básicos
- resumo consolidado

Exemplo de resumo:
- `total_items`
- `acquired_items`
- `pending_items`
- `completion_pct`
- `estimated_total`

### `GET /lists/{id}`
Deve retornar:
- dados da lista
- itens da lista
- resumo consolidado

## Interface proposta

### Página principal `Listas`
Elementos:
- título da página
- botão `Nova Lista`
- busca por nome
- filtro por tipo
- filtro por status

Exibição:
- cards de listas

Cada card deve mostrar:
- nome
- tipo
- total de itens
- itens concluídos
- percentual de progresso
- valor total estimado
- status

Ações por card:
- abrir
- editar
- arquivar
- excluir

### Página de detalhe da lista
Blocos:
- cabeçalho com nome, tipo, descrição e status
- resumo da lista
- tabela de itens

Tabela de itens:
- checkbox
- nome do item
- quantidade
- valor sugerido
- valor total
- observação
- ações

Ações por item:
- editar
- excluir
- marcar/desmarcar adquirido

## Ordem recomendada de implementação

### Etapa 1. Banco e backend base
- criar tabelas
- criar schemas
- criar repository
- criar endpoints de lista
- criar endpoints de item
- devolver consolidado pelo backend

### Etapa 2. Página principal
- rota/menu do módulo
- listagem
- filtros
- busca
- cards com resumo

### Etapa 3. Detalhe da lista
- cabeçalho da lista
- resumo
- CRUD de itens
- toggle de adquirido

### Etapa 4. Refinos
- mensagens de sucesso/erro
- estados vazios
- pequenos ajustes visuais
- smoke test manual

## Critérios de aceite da V1
- usuário cria uma lista
- usuário adiciona itens
- o total estimado é calculado corretamente
- o progresso muda ao marcar itens
- filtros e busca funcionam
- lista pode ser arquivada
- dados respeitam o workspace atual
- interface fica consistente com o padrão visual do DOMUS

## Evolução futura
Depois da V1, o módulo pode evoluir para:
- wishlist/desejos mais rica
- valor real pago
- comparação estimado x realizado
- conversão de item em lançamento financeiro
- modelos de lista
- recorrência

## Recomendação final
Seguir esta proposta como base oficial de implementação.

Ela mantém o módulo:
- útil desde a primeira versão
- simples de construir
- compatível com a arquitetura atual
- preparado para crescer sem retrabalho estrutural
