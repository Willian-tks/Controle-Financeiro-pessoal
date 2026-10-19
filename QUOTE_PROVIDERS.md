# DOMUS - Provedores de cotacoes

Mapeamento do codigo em 2026-10-19, para DOMUS-1.5-007. Plano informado pelo usuario: Gratuito, com 15.000 requisicoes por mes. O consumo real da conta nao foi consultado.

## Rotas atuais

| Classe / moeda | Ordem de tentativa em invest_quotes.py | Referencia |
|---|---|---|
| B3 em BRL, reconhecido por classe ou ticker | BRAPI se configurada; yfinance com ticker .SA; yfinance com ticker original; Yahoo chart HTTP | Preco na moeda do ativo |
| Stocks/ETFs US e ativos tratados como USD | Yahoo chart HTTP; Stooq | Preco diario na moeda do ativo |
| Cripto | Yahoo chart HTTP com par normalizado; yfinance | Par BASE-moeda, salvo quando ja informado no simbolo |
| Outros | yfinance; Yahoo chart HTTP | Depende do simbolo e da classificacao |

Renda fixa, Tesouro, fundos e COE tambem possuem fluxo proprio de valor/rentabilidade no sistema. O grupo Outros da coleta generica nao garante cobertura dessas classes.

## Datas e persistencia

- Yahoo chart usa preco e instante da mesma referencia, com tentativa de fechamento valido. Stooq retorna fechamento diario.
- BRAPI usa regularMarketTime quando disponivel; atualmente, se ausente/invalido, o codigo usa o dia da consulta. Essa referencia precisa ser distinguida antes de afirmar que toda data representa o mercado.
- A funcao yfinance efetiva usa o ultimo fechamento nao nulo de cinco dias. Ha duas definicoes no arquivo; a ultima e a vigente.
- Os precos salvos no banco permitem abrir a carteira sem consultar o provedor naquele momento. Custo medio e avisos de estimativa permanecem separados da coleta.
- A coleta generica nao possui cache com TTL explicito no modulo; nao confundir persistencia historica com garantia de atualizacao. Bibliotecas externas podem manter caches proprios.
- Timeout por ativo e paralelismo sao configuraveis e limitados em _resolve_quote_limits. Um timeout externo nao cancela a thread de consulta; nao aumentar a frequencia sem revisar esse comportamento.

## Primeira melhoria local

- Relatorio da sessao mostra preco unitario, moeda do cadastro, data retornada e fonte.
- Confirmacao distingue sucesso completo, falha parcial, nenhuma cotacao salva, selecao vazia e PTAX indisponivel.
- Cinco testes de mensagens adicionados ao CI; nenhuma nova chamada ou ampliacao de frequencia nesta etapa.

## Pendencias

- Estados estruturados implementados: no_data, rate_limited, access_denied, timeout, invalid_data, not_configured e provider_error. O relatorio inclui error_code, attempts e currency, preservando ok/error/src e o contrato de tupla/string das consultas. Falhas de todas as fontes HTTP tentadas permanecem identificadas; o wrapper yfinance legado nao informa a causa interna.
- Testes simulados cobrem HTTP 429/401/403/404/503, timeout, resultado vazio, alternativas, propagacao de diagnostico e rejeicao de preco/data invalidos. Corpos HTTP e URLs com credenciais nao sao copiados para as mensagens desses provedores.
- Revisar datas estimadas da BRAPI, cache, limites, alternativas e avisos na carteira.
- Plano gratuito e franquia confirmados pelo usuario. Documentacao publica consultada em 19/10/2026: 15.000 requisicoes por ciclo, um ticker por chamada, historico de ate tres meses e delay de acoes aproximado de 30 minutos. A data de renovacao e o consumo efetivo dependem do dashboard da conta; nao presumir reset no dia 1.
- A chamada atual por ticker respeita o limite de simbolos. Nenhuma ampliacao de frequencia, batching ou consumo foi introduzida. A cobertura de cada ativo/endpoints e limites de curto prazo ainda precisam ser conferidos antes de ampliar a coleta.
- Validar cenario real de falha e recuperacao no ambiente de teste; publicar somente no lote autorizado pelo usuario.

## Fontes publicas do plano

- https://brapi.dev/faq/api-e-gratis-mesmo
- https://web-next.brapi.dev/faq/quais-as-limitacoes
- https://web-next.brapi.dev/faq/como-a-api-e-calculada

## Validacao e publicacao desta etapa

94 testes Python, 18 testes Node e build Vite aprovados localmente. Suite Python completa executada fora do sandbox apos restricoes de arquivos temporarios na tentativa inicial. Sem migracao de banco ou novas dependencias. A futura publicacao exige atualizar/reiniciar o backend e gerar/promover o frontend; backend local recarregado para teste. VPS permanece sem alteracao.
