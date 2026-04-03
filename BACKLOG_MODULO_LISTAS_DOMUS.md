# Backlog Revisado - Módulo `Listas`

Data base: 2026-03-31
Revisado em: 2026-04-03

## Status executivo

O MVP do módulo `Listas` está funcionalmente implementado no backend e no frontend.

Neste momento, o backlog do módulo não precisa mais focar em novas entregas de produto da V1.
As pendências reais estão concentradas em validação final, rollout controlado e alinhamento documental.

## Escopo da V1 já fechado

- nome final do módulo: `Listas`
- escopo por `workspace_id`
- V1 sem integração automática com financeiro
- V1 sem recorrência, modelos, valor real pago ou metas complexas
- listas com status `ativa` e `arquivada`
- item com `sort_order`
- item com `completion_date`
- consolidado calculado no backend

## Implementação já concluída

- [x] Fase 1 - Modelo de dados
- [x] Fase 2 - Schemas e contratos de API
- [x] Fase 3 - Repositório e consolidado
- [x] Fase 4 - Endpoints FastAPI
- [x] Fase 5 - Navegação e entrada do módulo no frontend
- [x] Fase 6 - Tela principal de listas
- [x] Fase 7 - Tela de detalhe da lista
- [x] Fase 8 - UX e consistência visual
- [x] Cobertura automatizada de schema, repositório e API
- [x] Suíte automatizada do projeto validada em 2026-04-03
- [x] Build do frontend validado em 2026-04-03

## Pendências reais

### 1. Validação manual local

Status:
- [x] Revisado

Objetivo:
Confirmar o fluxo operacional completo do módulo no ambiente local antes do fechamento da V1.

Checklist:
- [ ] criar lista
- [ ] editar lista
- [ ] excluir lista
- [ ] arquivar lista
- [ ] adicionar item
- [ ] editar item
- [ ] excluir item
- [ ] marcar item como adquirido
- [ ] desmarcar item como adquirido
- [ ] validar atualização do resumo consolidado
- [ ] validar busca e filtros
- [ ] validar estados vazios
- [ ] validar uso básico em mobile

Critério de fechamento:
- [ ] fluxo principal executado sem erro visível no navegador

### 2. Validação de compatibilidade com PostgreSQL

Status:
- [ ] Pendente

Objetivo:
Reduzir risco de divergência entre ambiente local e VPS quando o backend subir fora do SQLite local.

Checklist:
- [ ] validar criação/migração das tabelas `lists` e `list_items` em PostgreSQL
- [ ] validar índices principais do módulo em PostgreSQL
- [ ] validar leitura e escrita básicas em PostgreSQL

Critério de fechamento:
- [ ] migração confirmada sem quebra e CRUD básico validado em PostgreSQL

### 3. Rollout controlado

Status:
- [ ] Pendente

Objetivo:
Publicar o módulo com baixo risco operacional para a base atual do DOMUS.

Checklist:
- [ ] publicar alterações no Git
- [ ] executar deploy no VPS conforme `VPS_LOCALWEB_DEPLOY.md`
- [ ] validar carregamento do módulo publicado
- [ ] executar smoke pós-deploy no VPS
- [ ] confirmar ausência de regressão visível em `Dashboard`
- [ ] confirmar ausência de regressão visível em `Lançamentos`
- [ ] confirmar ausência de regressão visível em `Investimentos`

Critério de fechamento:
- [ ] módulo publicado e validado sem regressão visível nos fluxos principais

### 4. Alinhamento documental mínimo

Status:
- [ ] Pendente

Objetivo:
Deixar a documentação compatível com o estado atual do módulo e com o rollout real.

Checklist:
- [x] revisar se a proposta ainda representa o que foi implementado
- [x] revisar se o checklist ainda representa apenas pendências reais
- [ ] registrar impacto de deploy se houver ajuste operacional adicional
- [x] alinhar documentação com campos atuais do módulo, incluindo diferenças já incorporadas no código

Critério de fechamento:
- [ ] documentação sem pendências enganosas ou escopo já superado

## Itens fora do backlog imediato

Estes pontos não devem voltar para o backlog da V1 sem nova decisão explícita:

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

## Próxima sequência recomendada

- [ ] 1. Rodar smoke manual local do módulo
- [ ] 2. Validar compatibilidade em PostgreSQL
- [ ] 3. Revisar documentação mínima
- [ ] 4. Publicar no Git
- [ ] 5. Fazer deploy controlado no VPS
- [ ] 6. Executar smoke pós-deploy e checar regressões

## Definição prática de concluído

O módulo `Listas` pode ser tratado como fechado nesta V1 quando:

- o smoke manual local estiver concluído
- a compatibilidade com PostgreSQL estiver validada
- o deploy no VPS estiver concluído
- o smoke pós-deploy não mostrar regressão visível
- a documentação mínima estiver coerente com o estado atual
