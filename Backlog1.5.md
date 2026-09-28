# DOMUS — Backlog 1.5

Versão-alvo do sistema: **1.5.0**
Criado em: **2026-09-21**
Estado: **Em andamento — revisão de valores e câmbio**
Objetivo: aumentar a confiabilidade dos números e simplificar o uso diário, preparando a base para lançamentos por IA e voz.

## Convenção de versionamento

- Cada versão planejada terá um documento `BacklogX.Y.md`, com itens identificados por `DOMUS-X.Y-NNN`.
- `X.Y.0`: entrega funcional da versão. `X.Y.Z`: correções compatíveis após a entrega. Mudanças incompatíveis exigem revisão da versão principal.
- Ao publicar, registrar versão, data, commit e tag Git `vX.Y.Z`, mudanças, validações e procedimento de reversão.
- Este documento define a versão-alvo; não afirma que a versão 1.5 já está publicada. O frontend ainda declara `0.1.0`; a identificação da versão será alinhada na preparação da entrega.
- Não alterar versões de dependências para acompanhar a versão do produto.
- Estados permitidos: Planejado, Em andamento, Bloqueado, Em validação e Concluído.
- Um item só será Concluído com seus critérios de aceite atendidos e evidências registradas. Código implementado e publicação em produção devem ser registrados separadamente.
- Correções urgentes podem ser entregues antes do restante da versão, com registro próprio de release.

## Prioridades

| Prioridade | Significado |
|---|---|
| P0 | Confiabilidade financeira e capacidade de publicar com segurança; executar primeiro |
| P1 | Redução do esforço diário e clareza da interface; núcleo da versão 1.5 |
| P2 | Evolução complementar ou preparação técnica; não deve atrasar P0/P1 |
| P3 | Exploração futura; fora do compromisso da versão 1.5 |

## Escopo e sequência da versão 1.5

Todos os itens abaixo começam em **Planejado**. As estimativas são relativas, não prazos: P = pequeno, M = médio, G = grande.

| ID | Prioridade | Entrega | Porte | Dependências |
|---|---|---|---|---|
| DOMUS-1.5-001 | P0 | Padronizar dependências e deploy Windows/Linux | M | Nenhuma |
| DOMUS-1.5-002 | P0 | Revisar valores, moedas e câmbio da carteira | G | Nenhuma |
| DOMUS-1.5-003 | P0 | Automatizar verificações de regressão e build | M | 001; acompanhar 002 |
| DOMUS-1.5-004 | P1 | Prototipar e implementar lançamento rápido | G | Protótipo primeiro; 003 para entrega |
| DOMUS-1.5-005 | P1 | Reorganizar Dashboard e indicadores | M | 002 e padrões de 004 |
| DOMUS-1.5-006 | P1 | Padronizar formulários, mensagens e experiência móvel | M | 004 e 005 |
| DOMUS-1.5-007 | P1 | Tornar fonte e atualização das cotações transparentes | M | 002 |
| DOMUS-1.5-008 | P2 | Separar gradualmente código dos módulos alterados | M | Executar junto de 004–007 |
| DOMUS-1.5-009 | P2 | Definir contrato de lançamento assistido por IA | M | 004 e regras do backend revisadas |
| DOMUS-1.5-010 | P1 | Consolidar documentação e publicar a versão 1.5 | M | 001–009 e 011 ou adiamento explícito registrado |
| DOMUS-1.5-011 | P1 | Ajuste explícito de posição de investimentos | M | 002 e 003 |

### DOMUS-1.5-001 — Dependências e deploy

Motivação: a cópia analisada contém 5.007 arquivos versionados em `frontend/node_modules`; o deploy anterior encontrou binário Windows no Linux.

- [x] Retirar `node_modules` do controle do Git e incluir no `.gitignore`, preservando os manifestos e lockfile necessários.
- [x] Definir versões suportadas de Node e Python e validar dependências reproduzíveis.
- [x] Revisar a política de `frontend/dist` e documentar onde o build é produzido.
- [x] Padronizar instalação, build, reinício da API, verificação de saúde e reversão no VPS.
- [x] Documentar backup antes de mudanças em dados/schema e preservação das configurações do servidor.

Aceite: checkout limpo gera build no Linux sem dependências copiadas do Windows; procedimento de deploy e reversão validado em ambiente controlado; nenhuma credencial adicionada ao Git.

### DOMUS-1.5-002 — Valores e câmbio

Estado: **Em validação** — implementação local pronta; diagnóstico de legado no VPS e validação após publicação pendentes.

Motivação: corrigimos descarte do câmbio de ETFs e conversão duplicada sem cotação; o código também usa o câmbio da última operação na avaliação da carteira.

- [x] Documentar unidades: preço na moeda do ativo, custo em BRL e valor de mercado em BRL.
- [x] Separar câmbio de aquisição de câmbio de avaliação; definir fonte, data de referência e comportamento sem atualização.
- [x] Preservar câmbio histórico das operações e não reescrever custos com câmbio atual.
- [x] Unificar a regra entre carteira, Dashboard, histórico e relatórios.
- [x] Definir avaliação histórica sem usar informações futuras.
- [x] Revisar custos, taxas, impostos, compras, vendas parciais e posições encerradas.
- [ ] Avaliar dados legados; qualquer reparo deve ter diagnóstico, backup e execução explícita.

Aceite: testes demonstram conversão única, consistência entre telas e histórico e identificação de dados estimados/desatualizados. O caso SPY de 0,64658795 × US$ 773,29 × 5,20 resulta em aproximadamente R$ 2.600,00 sem cotação, nunca R$ 13.520,00. Cotação disponível segue a política de avaliação definida.

### DOMUS-1.5-003 — Verificações automatizadas

Estado: **Em validação** — suíte SQLite e build local aprovados; novo job PostgreSQL aguarda execução no CI.

- [x] Configurar pipeline de testes Python e build do frontend em ambiente limpo.
- [x] Cobrir BRL/USD, ausência de cotação, câmbio, taxas e vendas parciais.
- [x] Verificar lançamentos, cartões, datas e isolamento entre workspaces nos fluxos alterados.
- [ ] Validar compatibilidade PostgreSQL dos caminhos modificados, além de SQLite.
- [x] Criar roteiro curto de teste funcional após deploy.

Aceite: falhas relevantes impedem liberar a versão; resultados ficam associados ao commit validado.

### DOMUS-1.5-004 — Lançamento rápido

Estado: **Em andamento — protótipo aprovado pelo usuário em 28/09/2026**. Proposta em `PROPOSTA_LANCAMENTO_RAPIDO.md`; integração ao sistema e validações com a API ainda pendentes.

- [x] Criar protótipo para celular e desktop antes de implementar o layout definitivo; usuário concluiu o teste e aprovou a proposta em 28/09/2026.
- [ ] Disponibilizar ação “Novo lançamento” a partir das telas principais.
- [ ] Selecionar Despesa, Receita ou Transferência explicitamente.
- [ ] Destacar valor, preencher data com hoje no fuso do usuário e oferecer contas/métodos favoritos.
- [ ] Mostrar categorias recentes e permitir repetir lançamento com revisão.
- [ ] Mover campos adicionais para “Mais opções”, preservando os fluxos de cartão e compromissos.
- [ ] Preparar o fluxo comum para futura entrada por texto, voz e foto de nota/cupom fiscal, sem botão inoperante na versão publicada.

Aceite: registrar despesa ou receita comum exige menos interações que o fluxo atual, medido com os mesmos cenários; usuário identifica conta, valor e data antes de salvar; não há regressão em transferências/cartões. Validar o protótipo com o responsável pelo produto.

### DOMUS-1.5-005 — Dashboard

- [ ] Separar saldo disponível, resultado do mês, compromissos e patrimônio.
- [ ] Explicitar período e base de cálculo dos indicadores.
- [ ] Distinguir custo investido, valor de mercado e resultado em investimentos.
- [ ] Simplificar hierarquia visual, reduzindo blocos com o mesmo destaque.
- [ ] Permitir acessar os lançamentos que compõem os principais totais.

Aceite: totais conferem com os dados detalhados sob os mesmos filtros; informações prioritárias são legíveis no celular e não dependem exclusivamente de cor.

### DOMUS-1.5-006 — Interface consistente

- [ ] Manter identidade azul com espaçamento, tipografia e contraste padronizados.
- [ ] Usar rótulos permanentes e mensagens de erro junto dos campos.
- [ ] Reduzir a área ocupada por confirmações de sucesso.
- [ ] Melhorar navegação por teclado, foco e nomes acessíveis dos controles.
- [ ] Adaptar tabelas/listas e ações às larguras móveis, sem perder informações financeiras relevantes.
- [ ] Validar estados vazio, carregando, erro e indisponibilidade.

Aceite: fluxos principais funcionam em celular e desktop, com teclado e sem campos/ações ocultos por problemas de layout.

### DOMUS-1.5-007 — Cotações e BRAPI

- [ ] Mapear os provedores atuais por classe e moeda; BRAPI já existe no projeto.
- [ ] Exibir fonte, data, moeda e estado da cotação, incluindo “Custo médio” quando usado como referência.
- [ ] Diferenciar consulta sem dados, falha de provedor e limite de consumo.
- [ ] Revisar cache, política de atualização e alternativas por provedor.
- [ ] Confirmar cobertura e condições do plano BRAPI utilizado antes de ampliar chamadas.

Aceite: falha de cotação não aparece como atualização bem-sucedida; valor estimado é identificável; API indisponível não impede abrir a carteira.

### DOMUS-1.5-008 — Organização do código

- [ ] Extrair componentes e lógica de Lançamentos durante a alteração desse fluxo.
- [ ] Separar módulos de Dashboard/Investimentos à medida que forem modificados.
- [ ] Centralizar formatação de moeda e componentes comuns relevantes.
- [ ] Separar regras de negócio de apresentação sem reescrever o sistema inteiro.

Aceite: módulos extraídos mantêm contratos e comportamento, com testes proporcionais às mudanças. Não transformar a entrega em refatoração geral.

### DOMUS-1.5-009 — Preparação para IA

- [ ] Definir contrato de rascunho: tipo, valor, moeda, data, conta, categoria, método, descrição e campos pendentes.
- [ ] Definir interpretação → validação → revisão → confirmação → gravação.
- [ ] Reutilizar regras e permissões do backend; a IA não recebe acesso direto ao banco.
- [ ] Definir comportamento para ambiguidades, cancelamento e reenvio sem duplicação.
- [ ] Planejar limites de uso, custos, segredos no backend e tratamento de áudio, texto e imagem, incluindo retenção e exclusão dos arquivos.
- [ ] Montar conjunto de frases e imagens de teste anonimizadas para avaliação futura.
- [ ] Imagem: extrair estabelecimento, data, moeda, total e itens quando legíveis; separar total pago de subtotal, desconto e troco. Campos incertos exigem revisão.
- [ ] Não inferir conta/cartão pelo cupom; usuário confirma forma de pagamento e categoria.
- [ ] Tratar fotos repetidas, documentos já lançados, imagens ilegíveis e múltiplos cupons; conteúdo do documento é dado, nunca instrução para a IA.
- [ ] Reutilizar o mesmo rascunho revisável para manual, texto, voz e imagem, sem gravar automaticamente.

Aceite: contrato e cenários documentados, inclusive “Gastei 42,90 no almoço, no débito do Inter” e “Recebi 1.500 de um serviço ontem”. Esta entrega é preparação; não inclui ativação de IA paga.

### DOMUS-1.5-010 — Documentação e release

- [ ] Conciliar AGENTS.md com os backlogs anteriores, sem marcar como concluído o que não foi verificado.
- [ ] Registrar a versão do produto de forma consistente e visível na aplicação.
- [ ] Produzir changelog, instruções de atualização e reversão.
- [ ] Registrar evidências de testes e validação de uso.
- [ ] Publicar de forma controlada e validar Dashboard, Lançamentos, Investimentos e permissões.

Aceite: versão, commit e data implantados são identificáveis; pendências e itens adiados estão registrados; confirmação de funcionamento após publicação.

### DOMUS-1.5-011 — Ajuste de posição de investimentos

Estado: **Planejado**. Prioridade: **P1**. Esforço: **M**. Dependências: 002 e 003.

Objetivo: permitir conciliação de posições sem cadastrar uma compra fictícia a preço zero.

- [ ] Criar operação explícita de ajuste, com ativo, data, quantidade, motivo obrigatório e custo informado na moeda do ativo; câmbio explícito quando aplicável.
- [ ] Definir acréscimo/redução de posição e efeitos no custo médio, histórico e rentabilidade, sem gerar receita/despesa ou resultado realizado fictício.
- [ ] Distinguir ajuste manual, transferência e bonificação; não presumir custo zero pela ausência de desembolso.
- [ ] Mostrar prévia de quantidade e custo antes/depois e exigir confirmação ao salvar.
- [ ] Registrar autor, data e motivo, respeitar workspace e permitir reversão rastreável.
- [ ] Cobrir BRL/USD, aumento/redução, custo zero justificado e consistência entre carteira, Dashboard e relatório.
- [ ] Revisar individualmente os lançamentos legados 85–88; nenhuma conversão ou alteração automática.

Aceite: ajuste identificado separadamente de compra/venda, com efeitos documentados, trilha de auditoria e testes; preservar registros antigos até conferência e autorização de eventual correção.

## Roadmap posterior — proposta, não compromisso de entrega da 1.5

| Versão sugerida | Prioridade | Entrega | Condição de entrada / aceite esperado |
|---|---|---|---|
| 1.6.0 | P1 | Lançamento por texto natural | Contrato 1.5-009 pronto; uma despesa/receita por frase; revisão, permissões, validação e proteção contra duplicação |
| 1.7.0 | P1 | Lançamento por voz | Reutilizar o fluxo por texto; gravar/transcrever, revisar e confirmar; medir qualidade em português, latência e custo; testar microfone nos navegadores-alvo |
| 1.8.0 | P1 | Lançamento por foto de nota ou cupom fiscal | Captura/upload, extração, revisão do total/data/estabelecimento e confirmação da conta; prevenção de duplicação e política de retenção; primeira entrega registra uma compra pelo total, sem rateio automático de itens |
| 1.9.0 ou posterior | P2 | Confirmação e correção por voz | Resolver campos ausentes por diálogo e confirmar verbalmente antes de gravar; versão exata depende do tamanho da entrega |
| A definir | P3 | Assistente de consultas financeiras e BRAPI/MCP | Validar necessidade, cobertura, permissões, custo e respostas com fonte/data; não permitir que a IA invente números da carteira |
| A definir | P3 | Frases com múltiplos lançamentos, parcelamentos e transferências | Somente após validar confiabilidade do fluxo simples |

Prioridade é relativa a cada etapa: voz é prioridade alta de produto, mas depende de um fluxo de gravação confiável. A sequência pode ser revista sem mudar silenciosamente o escopo de uma versão publicada.

## Fora do escopo da 1.5

- Lançar automaticamente sem revisão ou confirmação.
- Assistente que realiza operações de investimento.
- Aplicativo móvel nativo ou integração com WhatsApp.
- Migração ampla de framework ou reescrita completa.
- Novos recursos do módulo Listas sem decisão específica.

## Fechamento da versão

- [ ] Itens planejados concluídos ou adiados explicitamente com destino e motivo.
- [ ] Regras de cálculo verificadas e testes/build aprovados.
- [ ] Fluxos móveis e desktop revisados.
- [ ] Documentação e versão alinhadas.
- [ ] Deploy e reversão preparados.
- [ ] Publicação e teste funcional pós-deploy registrados.

## Registro de execução

Atualizar esta tabela durante o trabalho; manter os critérios acima como referência.

| Item | Estado | Evidência / commit | Validação local | Publicação / validação VPS |
|---|---|---|---|---|
| DOMUS-1.5-001 | Concluído | Produção f6ff746; backup /opt/apps/domus-backup.F0L2HZ | CI Linux, 64 testes isolados no VPS e 5 testes de reversão aprovados | Publicado; usuário confirmou login, Dashboard, Lançamentos e Investimentos |
| DOMUS-1.5-003 | Em andamento | Workflow DOMUS CI criado; dependência httpx declarada para testes | 59 testes Python locais aprovados; CI Linux aprovado no commit 7d01078 | CI publicado; VPS não validado |
| DOMUS-1.5-002 e 004 a 010 | Planejado | Backlog criado em 2026-09-21 | Não iniciada | Não publicada |

## Histórico do documento

| Data | Revisão | Alteração |
|---|---|---|
| 2026-09-21 | 1 | Criação do planejamento 1.5 e roadmap de IA, voz e consultas |


### Execução inicial — 2026-09-21

- `run_local.ps1` corrigido para herdar variáveis, registrar logs e verificar `index.html`.
- Removidos 5.007 arquivos de dependências do índice; nenhuma dependência local apagada.
- `dist` preservado nesta transição; build futuro preparado em pasta separada antes de publicação.
- Pendentes: instalação limpa/build Linux, dependências Python reproduzíveis, ensaio de promoção/reversão e validação no VPS.

### Verificações automáticas preparadas

- Workflow `.github/workflows/ci.yml` com jobs independentes de backend SQLite e build Linux.
- `requirements-dev.txt` inclui httpx para FastAPI TestClient.
- Suíte local: 59 testes aprovados. A instalação limpa e o build Linux permanecem pendentes da primeira execução remota.
- Proteção de branch com checks obrigatórios ainda não configurada. Não há deploy automático.

### Correção da primeira execução CI

- A execução GitHub Actions 35638743689 falhou no checkout dos dois jobs, antes dos testes.
- Causa: gitlink legado `Controle-Financeiro-pessoal` sem configuração `.gitmodules`.
- Referência órfã removida do índice; a pasta local estava vazia e não foi apagada.
- Nova execução Linux pendente após envio da correção.

### Retomada — 2026-09-22

- CI aprovado: execução [35639530907](https://github.com/Willian-tks/Controle-Financeiro-pessoal/actions/runs/35639530907), commit `7d01078`, verificada no GitHub na sessão anterior.
- Essa evidência supera as pendências históricas de primeira execução Linux acima: instalação e build do frontend e testes backend concluíram no CI.
- Os itens 001 e 003 permanecem em andamento: ainda faltam ensaio de publicação/reversão, dependências Python reproduzíveis, proteção de branch e verificações adicionais previstas.
- Ambiente local: API inicia pelo Codex; Vite encontra restrição de leitura neste ambiente e precisa ser iniciado pelo PowerShell do usuário, conforme validado na sessão anterior.

### Publicação e reversão do frontend — 2026-09-22

- Implementado `deploy/frontend_release.py`: promoção de dist-next, preservação de dist e reversão explícita por nome de backup.
- Cinco testes em diretórios temporários cobrem sucesso, candidato inválido, caminho inválido e falhas de promoção/reversão.
- Troca não atômica: exige janela controlada; não trata banco nem backend.
- CI executará os novos testes no próximo envio; ensaio Linux/VPS ainda pendente.
- Item 1.5-001 permanece Em andamento; ambiente local servido não foi alterado pelo ensaio.

### Ensaio isolado preparado — 2026-09-22

- Usuário informou aprovação do CI do commit `056ee88`.
- Extração limpa de apenas utilitário e testes do commit `056ee88` validada localmente em diretório temporário: 5 testes aprovados.
- Seção 13 do guia contém comandos para repetir no VPS sem atualizar o checkout de produção.
- O ensaio cobre renomeação, preservação e recuperação com builds mínimos; não valida o build servido nem Nginx.
- Execução no VPS depende do terminal do usuário; não há sessão SSH disponível nesta tarefa. Item 001 permanece Em andamento.

### Ensaio VPS aprovado — 2026-09-22

- Evidência: saída do terminal VPS enviada pelo usuário; commit extraído `056ee88`.
- Cinco testes executados em `/tmp/domus-release-test.*` com o Python do ambiente virtual do VPS: todos aprovados (`Ran 5 tests`, `OK`).
- Cobertura: promoção/reversão com builds mínimos, preservação das versões, rejeição de candidato inválido, proteção de caminho e recuperação de falhas simuladas.
- O comando executou `git fetch` e extraiu arquivos em pasta temporária; não atualizou o checkout servido nem reiniciou serviços.
- Esta evidência substitui a pendência do ensaio isolado no VPS nas notas anteriores. Não comprova publicação de um build real, configuração Nginx, interrupção abrupta ou reversão de backend/banco.
- Próxima etapa do item 001: tornar reproduzíveis as dependências Python; depois validar a publicação operacional real em janela controlada.
- Item 001 permanece Em andamento.

### Dependências Python fixadas — 2026-09-22

- Criados requirements.in/requirements-dev.in e locks de produção/testes com versões exatas e hashes, resolvidos para Python 3.12 em modo universal.
- requirements.txt, requirements-dev.txt e api/requirements.txt agora usam os locks; cache CI inclui os dois arquivos gerados.
- Instalação isolada Windows via uv sync com verificação de hashes: 41 pacotes; pip check sem incompatibilidades; 64 testes aprovados.
- Resolução baseada nas versões locais existentes. Pacotes de produção e testes têm versões compartilhadas coerentes.
- Aplicação local e ambiente do VPS não foram reinstalados.
- Validação Linux dos novos locks pendente do próximo CI; instalação de produção real permanece pendente. Item 001 segue Em andamento.

### Dependências validadas no VPS — 2026-09-22

- Usuário informou aprovação do CI para o commit `f6ff746`.
- Evidência enviada: execução em `/tmp/domus-python-test.6Ewspf`, com `Ran 64 tests in 26.731s` e `OK`.
- O procedimento fornecido extrai o commit `f6ff746` para uma pasta temporária, cria ambiente virtual separado, instala requirements-dev.txt e executa pip check antes dos testes com SQLite forçado. A chegada aos testes no bloco encadeado indica sucesso das etapas anteriores.
- Validada instalação isolada das dependências fixadas e suíte no VPS, sem atualização do checkout servido, reinício de serviços ou alteração do banco de produção pelo procedimento.
- Pendências anteriores de validação Linux/VPS dos locks estão resolvidas. Ainda faltam publicação controlada, conferência do serviço/Nginx e teste funcional pós-publicação.
- Item 1.5-001 permanece Em andamento até a validação operacional real. Não executar deploy apenas com base nesta anotação.

### Fechamento DOMUS-1.5-001 — 2026-09-22

- Publicação concluída no VPS no commit `f6ff746`, conforme saída enviada pelo usuário; Nginx válido, API saudável e checagem HTTPS aprovada.
- Backup: `/opt/apps/domus-backup.F0L2HZ`. Ambiente Python ativo preservado em `/opt/apps/domus-preparo.NeauFh/.venv`, referenciado por `/opt/apps/domus/.venv`; não remover essa pasta de preparação enquanto estiver em uso.
- Usuário confirmou login, Dashboard, carregamento dos Lançamentos e Investimentos funcionando em produção.
- Usuário percebeu melhora na troca de telas; observação subjetiva, sem benchmark antes/depois ou causa comprovada.
- Item 001 concluído. Notas anteriores de pendência desse item são históricas e superadas por este registro.
- Versões validadas: CI/local conforme arquivos de runtime; VPS com Node 20.20.1 e Python 3.12.3. Padronização futura de runtime deve preservar essa distinção.
- Item 003 continua em andamento (inclui verificações adicionais e proteção de branch). Próximo foco: DOMUS-1.5-002, valores e câmbio.

### Início DOMUS-1.5-002 — 2026-09-24

- Estado: Em andamento; primeira correção local do recorte histórico.
- Carteira com data final considera todas as operações até essa data, incluindo compras anteriores ao início do intervalo, e limita cotações e snapshots à data consultada.
- Valores atuais de renda fixa posteriores ao dia consultado não substituem snapshots históricos; sem snapshot válido, permanece a referência de custo.
- Novos testes cobrem compra anterior ao período, venda parcial, exclusão de compra/cotação futura e snapshots de renda fixa. Caso SPY de conversão única continua coberto.
- Política vigente: preços de operações e cotações na moeda do ativo; custo médio, custo total e avaliação consolidados em BRL. Sem cotação, o custo médio já convertido não deve receber câmbio novamente.
- Pendente: separar a referência cambial de avaliação do câmbio da última operação, expor fonte/data e revisar custos/relatórios/dados legados. Nenhuma alteração em dados de produção ou câmbio histórico de operações.
- Publicação desta etapa pendente; o item 002 não está concluído.
- Validação local: 66 testes Python aprovados; git diff --check sem erros.

### Implementação DOMUS-1.5-002 / 003 — 2026-09-24

- Política e roteiro de validação em `INVESTMENT_VALUATION.md`.
- Câmbio de avaliação separado do câmbio das operações: PTAX de venda/fechamento, persistida com data/fonte em tabela pública independente. Atualização manual e job de cotações integram a consulta; leitura da carteira não depende de rede.
- Mesmo motor para carteira/histórico; relatório respeita data final. Referências futuras são excluídas. Custo sem cotação não é convertido novamente.
- Carteira e relatório exibem origem/data do câmbio e avisos de estimativa/referência antiga. Dashboard identifica o total como valor de mercado em BRL.
- Validação de números finitos e despesas não negativas; diagnóstico de legado somente leitura em `audit_investments.py`. Cópia SQLite local consultada sem operações; base de produção ainda não auditada.
- Consulta real ao BCB aprovada, sem gravação na base local (fechamentos de 21–23/09/2026).
- CI ampliado com PostgreSQL 16 descartável e o mesmo contrato de testes de avaliação usado no SQLite. Não há PostgreSQL/Docker instalado neste ambiente; aprovação desse job depende do próximo envio ao GitHub.
- Build local realizado pela API JavaScript do Vite, importando o mesmo vite.config.js diretamente, pois o empacotamento da configuração pelo esbuild encontra restrição de leitura em pasta ancestral no Windows. Saída isolada em dist-next; configuração e dependências do projeto preservadas.
- Itens 002 e 003 ficam **Em validação**, sem declaração de conclusão antes das evidências pendentes. Nenhuma publicação ou alteração de operações de produção nesta etapa.
- Evidências finais locais: 76 testes Python aprovados, build frontend aprovado (aviso preexistente de bundle >500 kB), compilação Python e diff --check sem erros.

### Correção da preparação PostgreSQL — 2026-09-24

- CI #5 (commit 64976e8): SQLite e frontend aprovados; PostgreSQL falhou antes dos cálculos, na criação do usuário da fixture.
- Causa: literal inteiro 1 enviado para users.is_active, que é BOOLEAN no PostgreSQL. Corrigido para parâmetro Python True, compatível com ambos os drivers.
- Nove testes locais de avaliação/provedor aprovados após a correção. A execução PostgreSQL permanece pendente do novo CI; nenhum teste foi removido ou desativado.

### 2026-09-25 — Validacao de producao e correcao Yahoo (publicada e validada)

- Usuario confirmou sistema ativo e funcional apos deploy 4a813f2; stocks falharam com Yahoo HTTP 401.
- Coleta HTTP substituida de quote v7 para chart v8, com preco/data da referencia, validacao de valores finitos positivos e fallback para fechamento valido.
- Stooq permanece como alternativa; falhas das duas fontes passam a aparecer juntas.
- Consultas publicas locais AAL e SPY responderam com sucesso em 25/09; seis testes especificos e a suite completa de 82 testes passaram. Usuario confirmou cotacoes das stocks funcionando no VPS, sem HTTP 401, em 25/09/2026.
- Backup de producao informado como concluido em /opt/apps/domus-backup.heqPD4/database-retry.dump. Deploy 4a813f2 teve health OK e servico ativo.
- Diagnostico de legado e comparacao financeira final continuam pendentes. Esta correcao requer atualizar backend e reiniciar API; nao altera schema nem dependencias/frontend.

- Encerramento da correcao Yahoo: PR #2 integrado como ba93f1f, com seis checks aprovados; usuario confirmou publicacao e funcionamento das stocks. Esta evidencia encerra a falha de coleta, sem encerrar as pendencias financeiras dos itens 1.5-002/003.

### Diagnóstico de legado e ajuste de posição — 2026-09-25

- Consulta confirmada no PostgreSQL de produção em modo somente leitura: 115 operações verificadas, quatro alertas de preço e zero alterações. A tentativa anterior com zero operações consultou SQLite e não serve como evidência de produção.
- Workspace 1: IDs 85 (ITSA3, 6), 86 (KLBN11, 3), 87 (EZTC3, 27), 88 (BLAU3, 150), todos BUY em BRL em 06/03/2026, preço zero. Nenhum alerta cambial no diagnóstico executado.
- Usuário considera que provavelmente foram ajustes manuais; natureza e custo ainda não confirmados. Preservar os quatro registros. Custo médio e rentabilidade desses ativos permanecem pendentes de conferência.
- Usuário conferiu os valores que conseguiu e informou que aparentemente fecham; evidência parcial, não conciliação integral de todas as telas/relatórios.
- Aprovada inclusão do item 011 no planejamento; implementação não iniciada. Item 002 permanece em validação das exceções legadas.

### Retomada — lançamento rápido e imagem — 2026-09-28

- Usuário priorizou 004 e solicitou incluir foto de notas/cupons fiscais no escopo futuro, além de voz.
- Imagem prevista como P1 na versão sugerida 1.8.0; diálogo por voz deslocado para 1.9.0 ou posterior. Datas/versões continuam propostas de planejamento.
- Iniciado desenho do fluxo manual em PROPOSTA_LANCAMENTO_RAPIDO.md. Nenhum provedor de IA ativado; nenhuma alteração nos lançamentos de produção.

### Protótipo 1.5-004 — 2026-09-28

- Criado prototypes/lancamento-rapido.html, independente da aplicação, com dados fictícios e sem persistência.
- Inclui seleção de tipo, valor/data/contas, categorias, repetição, Mais opções, simulação de falha e confirmação. Cartão/compromissos sinalizam encaminhamento futuro ao fluxo completo; não simulam cálculos de fatura.
- Aberto em http://127.0.0.1:5175/lancamento-rapido.html. Repetição de despesa, confirmação e reinício verificados no navegador; modo compacto disponível no botão Ver celular.
- Aprovação visual, medição comparativa de interações e integração com API continuam pendentes. Voz/imagem permanecem no roadmap futuro.

### Aprovação do protótipo 1.5-004 — 2026-09-28

- Usuário concluiu o teste e aprovou: “Ficou ótimo, simples e rápido”.
- Aprovação qualitativa do protótipo; não houve medição formal comparativa de interações nem validação de gravação real.
- Próxima etapa: integrar o fluxo ao frontend e à API existentes, preservando permissões, cartões, transferências e rascunhos. Item 004 continua em andamento; nenhuma publicação de produção nesta etapa.

### Integração local do lançamento rápido — 2026-09-28

- Branch codex/quick-entry: componente QuickEntry integrado ao cabeçalho das telas, condicionado às permissões de visualizar/incluir lançamentos.
- Usa contas/categorias/transações do workspace e POST /transactions existente. Seleção explícita de tipo, data local, categorias recentes, repetição com revisão, observações e confirmação.
- Transferência envia origem/destino conforme contrato da API; não cria categoria de despesa. Compras no cartão e compromissos encaminham ao formulário completo com valor/data/descrição/observações e seleções preservados quando aplicáveis.
- Bloqueio de clique duplo durante envio; falha mantém rascunho. Falha na atualização dos painéis após gravação não induz nova gravação. Rascunho é reiniciado na troca de workspace; nenhum arquivo sensível é persistido.
- Oito testes Node de validação/payload passaram, incluídos no CI; 82 testes Python passaram. Build local aprovado, com aviso preexistente de bundle grande.
- Teste de navegador com o componente real em fixture isolada: transferência de R$ 200 com origem 1/destino 2, confirmação e falha de receita de R$ 1.500 mantendo campos. Nenhuma API/banco real foi usado nessa fixture.
- Pendente: teste autenticado ponta a ponta com dados descartáveis, cartões/compromissos no formulário completo, layout móvel com dados reais, CI remoto e publicação. Não declarar 004 concluído nem ganho medido de interações. Favoritos de conta/método ainda não implementados.

### 2026-09-28 - Validacao autenticada local do lancamento rapido

- SQLite local com duas contas e categorias ficticias identificadas por TESTE 1.5; producao nao alterada.
- Gravacao pela interface autenticada: despesa de R$ 42,90, receita de R$ 1.500,00 e transferencia de R$ 200,00. Historico confirmou quatro registros, incluindo debito na origem e credito no destino, total liquido R$ 1.457,10.
- Encaminhamento ao formulario de cartao preservou valor, descricao, categoria e data; compromisso preservou valor, descricao, categoria, conta e observacoes. Nao foram salvos cartao nem compromisso nesta verificacao.
- Corrigido submit involuntario ao encaminhar para cartao e limpar o rascunho; reabertura verificada sem mensagens de erro. Oito testes Node aprovados.
- Pendentes: gravacao completa de cartao/compromisso, validacao movel, favoritos, CI remoto e publicacao. Item 004 permanece em andamento.
