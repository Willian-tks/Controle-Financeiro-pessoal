# DOMUS — Backlog 1.5

Versão-alvo do sistema: **1.5.0**
Criado em: **2026-09-21**
Estado: **Em andamento — preparação de ambiente e CI**
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
| DOMUS-1.5-010 | P1 | Consolidar documentação e publicar a versão 1.5 | M | 001–009 ou adiamento explícito registrado |

### DOMUS-1.5-001 — Dependências e deploy

Motivação: a cópia analisada contém 5.007 arquivos versionados em `frontend/node_modules`; o deploy anterior encontrou binário Windows no Linux.

- [x] Retirar `node_modules` do controle do Git e incluir no `.gitignore`, preservando os manifestos e lockfile necessários.
- [ ] Definir versões suportadas de Node e Python e validar dependências reproduzíveis.
- [ ] Revisar a política de `frontend/dist` e documentar onde o build é produzido.
- [ ] Padronizar instalação, build, reinício da API, verificação de saúde e reversão no VPS.
- [ ] Documentar backup antes de mudanças em dados/schema e preservação das configurações do servidor.

Aceite: checkout limpo gera build no Linux sem dependências copiadas do Windows; procedimento de deploy e reversão validado em ambiente controlado; nenhuma credencial adicionada ao Git.

### DOMUS-1.5-002 — Valores e câmbio

Motivação: corrigimos descarte do câmbio de ETFs e conversão duplicada sem cotação; o código também usa o câmbio da última operação na avaliação da carteira.

- [ ] Documentar unidades: preço na moeda do ativo, custo em BRL e valor de mercado em BRL.
- [ ] Separar câmbio de aquisição de câmbio de avaliação; definir fonte, data de referência e comportamento sem atualização.
- [ ] Preservar câmbio histórico das operações e não reescrever custos com câmbio atual.
- [ ] Unificar a regra entre carteira, Dashboard, histórico e relatórios.
- [ ] Definir avaliação histórica sem usar informações futuras.
- [ ] Revisar custos, taxas, impostos, compras, vendas parciais e posições encerradas.
- [ ] Avaliar dados legados; qualquer reparo deve ter diagnóstico, backup e execução explícita.

Aceite: testes demonstram conversão única, consistência entre telas e histórico e identificação de dados estimados/desatualizados. O caso SPY de 0,64658795 × US$ 773,29 × 5,20 resulta em aproximadamente R$ 2.600,00 sem cotação, nunca R$ 13.520,00. Cotação disponível segue a política de avaliação definida.

### DOMUS-1.5-003 — Verificações automatizadas

- [ ] Configurar pipeline de testes Python e build do frontend em ambiente limpo.
- [ ] Cobrir BRL/USD, ausência de cotação, câmbio, taxas e vendas parciais.
- [ ] Verificar lançamentos, cartões, datas e isolamento entre workspaces nos fluxos alterados.
- [ ] Validar compatibilidade PostgreSQL dos caminhos modificados, além de SQLite.
- [ ] Criar roteiro curto de teste funcional após deploy.

Aceite: falhas relevantes impedem liberar a versão; resultados ficam associados ao commit validado.

### DOMUS-1.5-004 — Lançamento rápido

- [ ] Criar protótipo para celular e desktop antes de implementar o layout definitivo.
- [ ] Disponibilizar ação “Novo lançamento” a partir das telas principais.
- [ ] Selecionar Despesa, Receita ou Transferência explicitamente.
- [ ] Destacar valor, preencher data com hoje no fuso do usuário e oferecer contas/métodos favoritos.
- [ ] Mostrar categorias recentes e permitir repetir lançamento com revisão.
- [ ] Mover campos adicionais para “Mais opções”, preservando os fluxos de cartão e compromissos.
- [ ] Reservar entrada “Digitar ou falar” para ativação futura, sem botão inoperante na versão publicada.

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
- [ ] Planejar limites de uso, custos, segredos no backend e tratamento de áudio/texto.
- [ ] Montar conjunto de frases reais de receitas/despesas para avaliação futura.

Aceite: contrato e cenários documentados, inclusive “Gastei 42,90 no almoço, no débito do Inter” e “Recebi 1.500 de um serviço ontem”. Esta entrega é preparação; não inclui ativação de IA paga.

### DOMUS-1.5-010 — Documentação e release

- [ ] Conciliar AGENTS.md com os backlogs anteriores, sem marcar como concluído o que não foi verificado.
- [ ] Registrar a versão do produto de forma consistente e visível na aplicação.
- [ ] Produzir changelog, instruções de atualização e reversão.
- [ ] Registrar evidências de testes e validação de uso.
- [ ] Publicar de forma controlada e validar Dashboard, Lançamentos, Investimentos e permissões.

Aceite: versão, commit e data implantados são identificáveis; pendências e itens adiados estão registrados; confirmação de funcionamento após publicação.

## Roadmap posterior — proposta, não compromisso de entrega da 1.5

| Versão sugerida | Prioridade | Entrega | Condição de entrada / aceite esperado |
|---|---|---|---|
| 1.6.0 | P1 | Lançamento por texto natural | Contrato 1.5-009 pronto; uma despesa/receita por frase; revisão, permissões, validação e proteção contra duplicação |
| 1.7.0 | P1 | Lançamento por voz | Reutilizar o fluxo por texto; gravar/transcrever, revisar e confirmar; medir qualidade em português, latência e custo; testar microfone nos navegadores-alvo |
| 1.8.0 ou posterior | P2 | Confirmação e correção por voz | Resolver campos ausentes por diálogo e confirmar verbalmente antes de gravar; versão exata depende do tamanho da entrega |
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
| DOMUS-1.5-001 | Em andamento | Dependências removidas do índice Git; arquivos locais preservados; guia de deploy revisado; runtimes locais registrados | API e login local verificados; Linux e reversão pendentes | Não publicada |
| DOMUS-1.5-003 | Em andamento | Workflow DOMUS CI criado; dependência httpx declarada para testes | 59 testes Python aprovados; workflow Linux ainda não executado | Aguardando envio ao GitHub |
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
