# Valores, moedas e validação — DOMUS 1.5-002 / 003

## Unidades e regra de avaliação

- Preço, taxas e impostos de uma operação estão na moeda cadastrada no ativo (BRL ou USD).
- O câmbio informado na operação é BRL por USD e permanece registrado nela. Custo médio, custo total, resultado realizado, mercado e líquido estimado são expressos em BRL.
- Compras somam preço × quantidade e despesas, convertidos pelo câmbio da operação. Renda fixa preserva a regra existente: imposto é descontado no resgate, não na aplicação.
- Vendas retiram custo proporcional à quantidade pelo custo médio histórico. O resultado realizado usa o câmbio da venda, com desconto de taxas e impostos. Uma posição encerrada não conserva valor de mercado.
- Avaliação com cotação em USD: quantidade × cotação do ativo × PTAX de venda de fechamento mais recente até o dia avaliado. Custo de aquisição nunca é recalculado pela PTAX.
- Sem PTAX: mantém-se a estimativa pelo câmbio da última operação, com aviso e data explícitos. Não se apresenta essa taxa como câmbio atual.
- Sem cotação do ativo: usa-se o custo médio já em BRL, sem aplicar novo câmbio. A origem é “Custo médio” e o valor é identificado como estimativa.
- Proventos continuam sendo valores recebidos em BRL, conforme o contrato existente de gravação no caixa; não são convertidos novamente pela moeda do ativo.
- Renda fixa usa saldo/snapshot em BRL. Um saldo sem data comprovada não substitui uma posição histórica. O líquido replica o bruto enquanto não houver regra fiscal específica.
- A carteira atual considera operações até hoje em America/Sao_Paulo. O histórico e o relatório respeitam a data final e incluem compras anteriores ao início do intervalo; não utilizam referências futuras. O histórico é diário, não intradiário.
- Fonte/data do câmbio e avisos são retornados pela API e exibidos na carteira e no relatório. Cotação ou câmbio com mais de quatro dias corridos recebe aviso de referência antiga; isso não comprova falha do provedor (pode haver feriado).
- O Dashboard soma a mesma avaliação por ativo e chama esse total de “Valor de mercado (BRL)”, distinguindo-o do custo investido.

## PTAX e indisponibilidade

Fonte: [documentação do Banco Central](https://www.bcb.gov.br/conteudo/dadosabertos/BCBDepin/gnastportal-dados-abertostaxas-de-cambio---todos-os-boletins-diarios.pdf).
O módulo `invest_fx.py` consulta `CotacaoMoedaPeriodo`, moeda USD, somente boletim `Fechamento`, campo `cotacaoVenda`. A codificação de espaços usa `%20`, exigida pelo filtro do serviço.

Os fechamentos ficam em `investment_fx_rates`, uma tabela de dados públicos compartilhada, sem dados pessoais ou financeiros de workspaces. Ela é criada na inicialização tanto em SQLite quanto em PostgreSQL. Não há alteração das operações existentes.

A atualização manual de cotações e o job existente consultam os últimos 30 dias quando há ativos USD. Se o fechamento do dia já existe, usam o cache. Falhas mantêm as referências anteriores e aparecem como pendência; abrir carteira, Dashboard ou histórico não chama serviços externos.

Para preencher períodos anteriores, após iniciar a versão com a nova tabela, execute com o mesmo ambiente/banco da API, em intervalos de até 366 dias:

```bash
cd /opt/apps/domus
.venv/bin/python invest_fx.py --start 2026-01-01 --end 2026-09-24
```

Escolha datas conforme o período de investimentos. A rotina só grava referências públicas, não repara operações. Históricos podem mudar de uma estimativa cambial para a PTAX documentada após esse preenchimento.

## Diagnóstico de legado

`python audit_investments.py` faz somente consultas e informa IDs de operações com câmbio USD ausente/inválido, câmbio 1 que merece conferência, moeda fora da cobertura ou valores inválidos. Não possui modo de reparo e não considera câmbio 1 prova de erro.

O operador deve usar a configuração do banco real da API (inclusive DATABASE_URL, caso PostgreSQL). Na cópia SQLite local consultada em 24/09/2026 não havia operações; isso não valida os dados do VPS. No VPS, revisar a saída contra os comprovantes. Qualquer reparo exige backup, diagnóstico individual e execução explicitamente autorizada.

## Verificações e liberação

- SQLite: `python -m unittest discover -s tests -p 'test_*.py' -v`.
- PostgreSQL: o CI cria serviço PostgreSQL 16 descartável. `tests/integration/test_postgres_valuation.py` executa o mesmo contrato de avaliação, API/resumo/relatório, taxas, venda parcial, encerramento, cache e isolamento. A variável `DOMUS_POSTGRES_TEST_URL` só aceita banco local `domus_ci_test`; nunca usar banco de produção.
- Frontend: CI Linux executa `npm ci --include=dev --include=optional` e build de `dist-next`.
- Publicar somente o commit com todos os jobs aprovados. O CI não faz deploy automático. Proteção de branch com checks obrigatórios deve ser verificada nas configurações do GitHub; este documento não afirma que ela esteja habilitada.

Checklist funcional após publicação (registrar commit e data):

1. Confirmar saúde da API e login; abrir Lançamentos e cartão/fatura existentes.
2. Atualizar cotações incluindo um ativo USD; conferir mensagem PTAX e data/fonte na carteira.
3. Conferir custo histórico preservado e valor USD convertido uma única vez. Sem cotação, o exemplo SPY 0,64658795 × 773,29 × 5,20 continua próximo de R$ 2.600,00.
4. Comparar a soma de mercado da carteira com o Dashboard, sob as mesmas classes. Exportar relatório para a mesma data e comparar.
5. Conferir histórico anterior a uma operação/cotação recente e que dados de outro workspace não aparecem.
6. Executar o diagnóstico de legado no banco correto, sem aplicar reparos.

Deploy segue `VPS_LOCALWEB_DEPLOY.md`: backup prévio, backend atualizado/reiniciado para criar a tabela, frontend reconstruído e promovido. Rollback restaura código, ambiente e build anteriores; a tabela pública nova pode permanecer, pois o código antigo a ignora. Não remover a venv ativa do preparo nem alterar operações para fazer rollback.
