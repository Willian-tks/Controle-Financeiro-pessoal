# Backlog Técnico MVP - Rentabilidade Renda Fixa

Data base: 2026-03-02

## Decisões Fechadas (travadas)

1. Base temporal para conversão de taxa anual: **252 dias úteis**.
2. IPCA: aplicação **no fechamento do mês**.
3. Precisão:
4. Taxas: **8 casas decimais**.
5. Valores intermediários: **6 casas decimais**.
6. Não arredondar no cálculo diário.
7. Arredondar **apenas no momento de salvar `current_value`**.
8. Momento de atualização: **ao abrir a aba Investimentos**.

## Objetivo do MVP

Permitir cálculo automático de rentabilidade acumulada para ativos de renda fixa com os modos:

1. Prefixado
2. % do CDI
3. % do SELIC
4. IPCA + spread
5. Manual (sem cálculo automático)

## Fase 1 - Modelo de dados

1. Adicionar campos no cadastro de ativos:
2. `rentability_type` (`PREFIXADO`, `PCT_CDI`, `PCT_SELIC`, `IPCA_SPREAD`, `MANUAL`)
3. `index_name` (`CDI`, `SELIC`, `IPCA`, `NULL`)
4. `index_pct` (REAL)
5. `spread_rate` (REAL)
6. `fixed_rate` (REAL)
7. `principal_amount` (REAL)
8. `current_value` (REAL)
9. `last_update` (DATE)
10. Criar tabela de séries econômicas:
11. `index_rates(index_name, ref_date, value, source, created_at, updated_at, user_id opcional)`
12. Criar índice único: `index_name + ref_date`.
13. Criar migração para SQLite/Postgres.
14. Backfill inicial:
15. Ativo de renda fixa sem configuração -> `MANUAL`.
16. `principal_amount` inicial = custo atual quando possível.

Critério de aceite:

1. Migração executa sem perda de dados.
2. Leitura/escrita dos novos campos funcionando nos repositórios.

## Fase 2 - Ingestão de índices (CDI/SELIC/IPCA)

1. Criar serviço para salvar séries em `index_rates`.
2. Garantir idempotência por `index_name + ref_date`.
3. CDI/SELIC com periodicidade diária.
4. IPCA com periodicidade mensal.
5. Criar endpoint interno/admin para carga/atualização.

Critério de aceite:

1. Reprocessar mesma janela não duplica registros.
2. Séries ficam disponíveis para o motor de cálculo.

## Fase 3 - Motor de cálculo incremental

1. Implementar função `update_investment_value(asset_id, as_of_date=today)`.
2. Fluxo:
3. Carregar `principal_amount`, parâmetros de rentabilidade, `last_update`, `current_value`.
4. Determinar intervalo `last_update + 1` até `as_of_date`.
5. Aplicar cálculo por tipo:
6. `PREFIXADO`: taxa anual -> fator diário (base 252 úteis).
7. `PCT_CDI`: taxa CDI diária * percentual.
8. `PCT_SELIC`: taxa SELIC diária * percentual.
9. `IPCA_SPREAD`: aplicar IPCA no fechamento do mês + spread anual convertido.
10. `MANUAL`: não altera valor automaticamente.
11. Usar 8 casas para taxas e 6 casas nos intermediários.
12. Não arredondar por dia.
13. Arredondar somente no `current_value` persistido.
14. Atualizar `last_update` e `current_value` em transação única.

Critério de aceite:

1. Duas execuções no mesmo dia não alteram novamente o resultado.
2. Resultado consistente para intervalo longo e curto.

## Fase 4 - Validações de negócio (API)

1. `PCT_CDI` e `PCT_SELIC` exigem `index_name` e `index_pct`.
2. `IPCA_SPREAD` exige `index_name=IPCA` e `spread_rate`.
3. `PREFIXADO` exige `fixed_rate`.
4. `MANUAL` não exige campos de taxa.
5. Bloquear combinações inconsistentes e `NULL` inválido.

Critério de aceite:

1. API retorna erros claros e padronizados para payload inválido.

## Fase 5 - Integração no fluxo "abrir Investimentos"

1. No carregamento da página Investimentos, disparar atualização de ativos elegíveis.
2. Estratégia recomendada:
3. Rodar atualização antes de montar dados de resumo/carteira.
4. Proteger com timeout e tratamento de falha parcial (sem derrubar tela).
5. Garantir que atualização não degrade UX perceptivelmente.

Critério de aceite:

1. Ao abrir Investimentos, dados já aparecem atualizados conforme índices disponíveis.

## Fase 6 - Frontend (Editar Ativo)

1. Exibir seção dinâmica quando classe for renda fixa.
2. Campo "Tipo de Rentabilidade" com:
3. Prefixado
4. % do CDI
5. % do SELIC
6. IPCA + X
7. Manual
8. Regras de exibição:
9. Prefixado -> `Taxa anual (%)`
10. % CDI/% SELIC -> `Percentual do índice`
11. IPCA + X -> `Spread anual (%)`
12. Manual -> sem campos extras
13. Mostrar `last_update` e `current_value` no detalhe do ativo.

Critério de aceite:

1. UI impede combinação inválida antes do submit.

## Fase 7 - Testes

1. Testes unitários do motor por tipo de rentabilidade.
2. Testes de fronteira:
3. mudança de mês/ano
4. ausência de índice no período
5. ativo com `last_update` nulo
6. Testes de API para validações de payload.
7. Teste E2E mínimo: abrir Investimentos atualiza valores automaticamente.

Critério de aceite:

1. Suíte cobre cenários felizes e erros críticos.

## Fase 8 - Rollout controlado

1. Habilitar para novos ativos primeiro.
2. Recalcular ativos legados em lote.
3. Monitorar divergência entre valor esperado e valor calculado.
4. Disponibilizar fallback `MANUAL` por ativo.

Critério de aceite:

1. Sem regressão nos relatórios existentes de investimentos.

