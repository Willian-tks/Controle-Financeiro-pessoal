# Checklist de Fechamento - Módulo `Listas`

Atualizado em: 2026-04-03

## Contexto

Este checklist não cobre mais a construção do MVP.
Ele existe para fechar a V1 com segurança operacional, validação mínima e documentação coerente.

## 1. Smoke manual local

- [ ] abrir a página `Listas`
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
- [ ] validar busca por nome
- [ ] validar filtros por tipo e status
- [ ] validar estado vazio sem listas
- [ ] validar estado vazio sem itens
- [ ] validar comportamento básico em mobile

## 2. Compatibilidade de banco

- [ ] validar migração em SQLite
- [ ] validar migração em PostgreSQL
- [ ] validar CRUD básico em PostgreSQL
- [ ] validar índices principais do módulo em PostgreSQL

## 3. Validação automatizada já exigida antes de publicar

- [x] rodar suíte automatizada relevante do projeto
- [x] confirmar que o módulo `Listas` segue coberto por testes de schema, repositório e API
- [x] rodar build do frontend

## 4. Documentação mínima

- [x] revisar `PROPOSTA_MODULO_LISTAS_DOMUS.md`
- [x] revisar `BACKLOG_MODULO_LISTAS_DOMUS.md`
- [x] alinhar este checklist com o estado real do módulo
- [ ] registrar qualquer impacto operacional de deploy, se houver
- [x] confirmar que a documentação não deixa pendências já concluídas como se ainda fossem escopo aberto

## 5. Publicação e rollout

- [ ] publicar no Git
- [ ] executar deploy no VPS conforme `VPS_LOCALWEB_DEPLOY.md`
- [ ] validar carregamento do frontend publicado
- [ ] validar endpoints principais do módulo publicado
- [ ] executar smoke pós-deploy do fluxo principal de `Listas`

## 6. Checagem de regressão

- [ ] confirmar ausência de regressão visível em `Dashboard`
- [ ] confirmar ausência de regressão visível em `Lançamentos`
- [ ] confirmar ausência de regressão visível em `Investimentos`
- [ ] confirmar ausência de regressão visível em navegação/autenticação

## Gate antes de usuário real

- [ ] smoke manual local concluído
- [ ] validação em PostgreSQL concluída
- [ ] deploy controlado concluído
- [ ] smoke pós-deploy concluído
- [ ] regressões principais não detectadas
- [ ] documentação mínima coerente com o estado publicado
