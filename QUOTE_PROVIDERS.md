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
- BRAPI exige regularMarketTime valido, em epoch, dia ISO ou instante ISO com fuso. Instantes sao convertidos para America/Sao_Paulo. Datas ausentes, invalidas ou futuras rejeitam a resposta e permitem as alternativas existentes; a data da coleta nunca substitui a data de mercado.
- A funcao yfinance efetiva usa o ultimo fechamento nao nulo de cinco dias. Ha duas definicoes no arquivo; a ultima e a vigente.
- Os precos salvos no banco permitem abrir a carteira sem consultar o provedor naquele momento. Custo medio e avisos de estimativa permanecem separados da coleta.
- A coleta generica possui cache em memoria por processo, compartilhado apenas para dados publicos da mesma combinacao simbolo/classe/moeda. Resultados validos duram 1.800 segundos; falhas duram 60 segundos e nunca se tornam sucesso. Os parametros opcionais QUOTE_CACHE_TTL_S e QUOTE_ERROR_CACHE_TTL_S aceitam de 0 a 3.600 segundos; zero desabilita a reutilizacao da categoria. O cache e limitado a 512 entradas e usa relogio monotono.
- Consultas concorrentes da mesma chave aguardam a consulta em andamento. O relatorio indica cache_hit, cache_age_s e fetched_at, preservando fonte e data de mercado. O asset_id e remapeado para o ativo da requisicao, sem compartilhar identificadores entre workspaces. Memoria e invalidada ao reiniciar o processo; API workers e job CLI possuem caches independentes.
- Cache nao e controle global de franquia. O consumo real precisa ser acompanhado no dashboard BRAPI, incluindo outros processos, usuarios e consultas manuais. Credenciais alteradas exigem reiniciar o processo para descartar referencias da configuracao anterior.
- Timeout por ativo e paralelismo sao configuraveis e limitados em _resolve_quote_limits. Um timeout externo nao cancela a thread de consulta; nao aumentar a frequencia sem revisar esse comportamento.

## Primeira melhoria local

- Relatorio da sessao mostra preco unitario, moeda do cadastro, data retornada e fonte.
- Confirmacao distingue sucesso completo, falha parcial, nenhuma cotacao salva, selecao vazia e PTAX indisponivel.
- Cinco testes de mensagens adicionados ao CI; nenhuma nova chamada ou ampliacao de frequencia nesta etapa.

## Estado da implementacao

- Estados estruturados implementados: no_data, rate_limited, access_denied, timeout, invalid_data, not_configured e provider_error. O relatorio inclui error_code, attempts e currency, preservando ok/error/src e o contrato de tupla/string das consultas. Falhas de todas as fontes HTTP tentadas permanecem identificadas; o wrapper yfinance legado nao informa a causa interna.
- Testes simulados cobrem HTTP 429/401/403/404/503, timeout, resultado vazio, alternativas, propagacao de diagnostico e rejeicao de preco/data invalidos. Corpos HTTP e URLs com credenciais nao sao copiados para as mensagens desses provedores.
- Carteira exibe moeda do ativo e fonte do valor separadas da origem da avaliacao. Custo medio, ajuste manual e motor de rentabilidade nao sao apresentados como preco obtido de um provedor. Cotacoes antigas e estimativas mantem os avisos financeiros existentes.
- Plano gratuito e franquia confirmados pelo usuario. Documentacao publica consultada em 19/10/2026: 15.000 requisicoes por ciclo, um ticker por chamada, historico de ate tres meses e delay de acoes aproximado de 30 minutos. A data de renovacao e o consumo efetivo dependem do dashboard da conta; nao presumir reset no dia 1.
- A chamada atual por ticker respeita o limite de simbolos. Nenhuma ampliacao de frequencia ou batching foi introduzida; o cache reduz repeticoes. Stocks e cripto mantem seus provedores proprios; a cobertura BRAPI nao e presumida para essas classes. Respostas de acesso negado ou sem dados continuam explicitas. Novos endpoints, maior frequencia ou outras coberturas exigem nova verificacao do plano e do consumo.
- Historico existente e preservado: datas antigas produzidas pelo comportamento anterior nao sao corrigidas nem reconstruidas automaticamente. A recusa de data sintetica vale para novas consultas.
- Implementacao local finalizada; conferir os novos campos no navegador e validar o lote no VPS apos CI/publicacao. Nao houve interrupcao de provedores externos ou consumo de franquia nos testes simulados.

## Fontes publicas do plano

- https://brapi.dev/faq/api-e-gratis-mesmo
- https://web-next.brapi.dev/faq/quais-as-limitacoes
- https://web-next.brapi.dev/faq/como-a-api-e-calculada

## Validacao e publicacao desta etapa

Primeira etapa: 94 testes Python, 18 testes Node e build Vite aprovados. Fechamento: 103 testes Python, 19 testes Node e build aprovados; testes adicionais cobrem datas BRAPI, fuso, referencia invalida, cache, expiracao, isolamento por moeda, remapeamento de ativo e recuperacao de falha. A suite financeira confere fonte preservada, custo medio e origem de saldo manual. Sem migracao de banco ou novas dependencias. A publicacao do fechamento exige atualizar/reiniciar o backend e gerar/promover o frontend. Nenhuma publicacao deste fechamento foi executada no VPS.
