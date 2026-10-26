# DOMUS - Contrato de rascunho assistido

DOMUS-1.5-009. Revisao 1, 2026-10-26. **Preparacao, nao implementacao de IA.**
Nao ha provedor contratado, endpoint novo, upload, chamada paga ou gravacao
automatica nesta entrega. As exigencias futuras abaixo sao bloqueios de ativacao.

## Escopo e referencias

Manual, texto, voz transcrita e imagem convergem para o mesmo rascunho revisavel.
A primeira entrega assistida futura aceita uma despesa ou receita por entrada.
Transferencias, recorrencia, parcelas, investimentos e pagamento futuro seguem
para os formularios existentes, sem conversao silenciosa para despesa simples.

Referencias atuais: api/schemas.py (TransactionCreateRequest),
api/main.py (create_transaction, _current_user e verificacao de permissoes),
frontend/src/quickEntry.js (quickPayload e quickCreditCard).
A IA interpreta dados; nao decide autorizacao, nao chama o repositorio e nao
recebe credenciais do banco, token de sessao ou historico financeiro completo.

## Contrato v1 proposto

Envelope controlado pelo servidor, nunca confiado ao modelo:

| Campo | Regra |
|---|---|
| schema_version | Literal 1 |
| draft_id / revision | UUID do servidor e inteiro crescente; edicao invalida confirmacao anterior |
| user_id / workspace_id | Identidade autenticada; rejeitar escopo enviado pelo modelo |
| source | manual, text, audio ou image |
| status | interpreting, needs_review, ready, saving, saved, cancelled, expired ou failed |
| reference_date / timezone | Data civil e fuso do usuario capturados na entrada; sem usar UTC implicitamente |
| expires_at | Expiracao proposta de 24 horas; nao gravar rascunho expirado |
| fields | Campos abaixo, com null para desconhecido |
| pending_fields | Nomes de campos ausentes, ambiguos ou ainda sem confirmacao |
| warnings | Codigos e mensagens para revisao; nunca comandos executaveis |
| evidence | Trechos curtos ou regioes da imagem, sem dados pessoais desnecessarios |
| receipt | Dados auxiliares abaixo, ou null |

Campos revisaveis em fields:

| Campo | Tipo / validacao |
|---|---|
| kind | Despesa ou Receita; outros fluxos exigem formulario completo |
| amount | String decimal positiva canonica, por exemplo "42.90"; Decimal no servidor, rejeitar NaN, infinito e sinal negativo |
| currency | Codigo ISO da moeda, confirmado; nao converter valores automaticamente |
| date | YYYY-MM-DD valido; expressao relativa resolvida no reference_date/timezone |
| account_id | Inteiro de conta acessivel no workspace; obrigatorio confirmar |
| category_id | Inteiro de categoria compativel com kind; sugestao nao e confirmacao |
| method | PIX, Debito, TED ou Dinheiro conforme fluxo atual; Credito e Futuro abrem formulario completo |
| description | Texto simples, revisavel; padrao atual por categoria so apos validacao |
| notes | Texto opcional, sem copiar documento/transcricao integral por padrao |
| source_account_id / card_id | null nesta primeira entrega; nao perder dados se encaminhar ao fluxo completo |

Sugestoes de nomes nao sao IDs: account_hint e category_hint podem ajudar a
interface, mas resolucao deve usar o cadastro autorizado atual. Duas contas
chamadas Inter deixam account_id pendente. Nunca inventar IDs ou cadastros.
Validar saida com lista fechada de campos, tipos e limites; rejeitar campos extras
como SQL, ferramentas ou instrucoes. Confianca do modelo nao dispensa revisao.

receipt contem merchant, document_date, currency, subtotal, discount,
total_paid, tendered, change e items (description, quantity, unit_price, total).
Campos monetarios usam a mesma representacao decimal; campos ilegíveis ficam null.
O valor do lancamento e o total pago, nao subtotal, dinheiro entregue ou troco.
Itens sao auxiliares: uma compra pelo total, sem rateio automatico na primeira entrega.
Discordancia entre totais ou soma dos itens produz aviso; nao corrigir por palpite.
Recibo nao confirma conta, cartao, categoria nem meio de pagamento do usuario.

## Fluxo e estados

1. Entrada autenticada: verificar acesso, limites e consentimento antes do envio.
2. Interpretacao: produzir somente campos propostos; falha permite entrada manual.
3. Validacao: tipos, decimal, data, moeda, IDs autorizados e categoria/tipo.
4. Revisao obrigatoria: mostrar todos os campos, origem e incertezas. Nao salvar
   enquanto houver pending_fields; todos os campos financeiros precisam de aceite.
5. Confirmacao explicita: usuario confirma a revisao exata. Revalidar permissoes,
   workspace ativo e cadastros no servidor imediatamente antes da gravacao.
6. Gravacao unica: usar o servico de regras do fluxo atual, com idempotencia
   transacional; retornar IDs criados. So entao status saved e mensagem de sucesso.

Qualquer edicao cria nova revisao e volta a needs_review. Mudar workspace invalida
o rascunho aberto. Cancelar antes do commit encerra o rascunho sem lancamento.
Se o commit ja ocorreu, retornar saved: cancelar nao apaga movimento financeiro;
exclusao ou correcao usa o fluxo existente com permissao e confirmacao.
Falha de interpretacao nao pode bloquear o formulario manual.

### Compatibilidade com o backend

O POST /transactions atual recebe amount numerico e nao recebe currency;
nao encaminhar o envelope diretamente. O adaptador futuro deve conferir a moeda
da conta e a semantica BRL do fluxo atual antes de gerar TransactionCreateRequest.
Moeda estrangeira ou conversao pendente exige formulario apropriado ou bloqueio,
nunca assumir BRL ou usar cotacao da IA. Valor e magnitude positiva; sinal financeiro
e decidido pelo backend a partir de kind/categoria, nao pelo modelo.
Transferencia usa account_id como destino e source_account_id como origem:
nao reutilizar o mapeamento de despesa nesse fluxo.
Credito exige cartao autorizado vinculado a conta e regras de fatura existentes;
Futuro preserva vencimento/parcelas no formulario completo.

### Reenvio e duplicacao (requisito ainda nao implementado)

O POST atual nao possui chave de idempotencia. Desabilitar botao nao resolve
timeout ou duas abas. Antes de ativar gravacao assistida, implementar chave unica
por workspace + usuario + draft_id + revision, com hash do payload confirmado,
reserva e criacao do lancamento na mesma transacao do banco.
Mesma chave e hash retornam o resultado original; hash diferente retorna conflito.
Concorrencia deve criar exatamente um movimento. A chave nao deve expirar de modo
a permitir regravar revisao salva; conservar referencia minima junto ao movimento.
Teste obrigatorio em SQLite e PostgreSQL, incluindo timeout apos commit.

Nova foto do mesmo cupom pode gerar nova chave: detectar hash de arquivo e
identificador fiscal quando disponivel, mais candidatos por data/valor/estabelecimento
no mesmo workspace. Hash nao detecta todas as fotos diferentes; correspondencia
aproximada apenas alerta e pede decisao, sem bloquear compras legitimas iguais.
Nao reenviar POST automaticamente quando resultado e desconhecido: consultar
resultado idempotente e permitir retomada. Essa consulta tambem exige autorizacao.

## Ambiguidades e documentos

- "Ontem" usa data de referencia capturada; sem fuso confiavel, pedir data.
- Valor ausente, moeda incerta, varias compras ou contradicoes deixam campos pendentes.
- Texto/voz pode sugerir metodo ou conta, mas usuario confirma o cadastro resolvido.
- Foto ilegivel pede outra imagem ou entrada manual; varios cupons pedem separacao.
- Instrucao no documento, EXIF ou transcricao e dado nao confiavel. Ignorar pedidos
  de mudar regras, enviar segredos, chamar URLs ou gravar sem confirmacao.
- OCR parcial nao autoriza inventar campos. Recusar arquivos executaveis,
  conteudo remoto e formatos fora da lista; remover metadados antes de enviar.

## Limites, privacidade e custos propostos

IA desativada por padrao. Antes de ativar: definir provedor, verificar precos,
termos de retencao/regiao, aprovar orcamento e disponibilizar consentimento.
Nenhum preco ou capacidade comercial e assumido neste contrato.
Limites iniciais propostos, configuraveis no backend: texto ate 2.000 caracteres,
audio ate 60 segundos e 10 MB, imagem ate 10 MB e 20 megapixels apos decodificacao;
aceitar JPEG/PNG/WebP validados por assinatura e decodificacao, nao apenas extensao.
Uma imagem/cupom por rascunho, duas tentativas por entrada, uma chamada simultanea
por usuario, 20 interpretacoes por usuario/dia e 100 por workspace/dia.
Reservar quota antes de chamada, contar falhas cobraveis e limitar saida/timeouts.
Definir teto monetario mensal por workspace e global (obrigatorio, sem padrao
ilimitado), registrar uso real e bloquear antes de exceder a reserva estimada.
Sem retry ilimitado, polling ou envio de toda a carteira ao provedor.

Chaves so no backend/secret manager, nunca VITE_*, repositorio, navegador ou logs.
Nao reutilizar chaves BRAPI como credenciais de IA. Logs guardam IDs, estado,
latencia e uso, nao prompt, imagem, audio, transcricao ou dados bancarios.
Upload privado isolado por workspace, URL curta assinada somente quando necessaria,
validacao antimalware e limites de memoria/tempo antes do processamento.
Apagar originais temporarios ao concluir/cancelar/falhar; varredura de residuos
em ate 24 horas. Rascunhos nao salvos expiram em 24 horas. Documento original
nao vira anexo permanente sem funcionalidade e consentimento separados.
Transcricao segue a mesma retencao do rascunho; salvar apenas descricao/notas
confirmadas. Provedor deve oferecer retencao compativel ou nao sera aprovado.
Exclusao local nao promete exclusao remota imediata: documentar prazo contratual
e permitir pedido de exclusao ao provedor. Auditoria financeira minima de movimento
salvo permanece conforme politica do produto, separada de arquivos e prompts.

## Avaliacao e bloqueios de ativacao

Corpus sintetico em tests/fixtures/ai_drafts/cases.json e receipts/*.svg;
nenhuma conta/pessoa real. SVG e matriz legivel de avaliacao, nao formato de
upload permitido. Renderizar para PNG/JPEG ao avaliar OCR; incluir futuramente
capturas desfocadas, rotacionadas e fotos reais anonimizadas com consentimento.
Fixtures representam resultados esperados, nao resultados de um modelo executado.

Exemplos obrigatorios: "Gastei 42,90 no almoço, no débito do Inter" produz despesa
42.90, Debito e sugestao Inter; data, moeda, conta e categoria precisam de revisao.
"Recebi 1.500 de um serviço ontem", com referencia 2026-10-26 em America/Sao_Paulo,
produz receita 1500.00 em 2026-10-25; metodo, moeda, conta e categoria pendentes.

Antes de liberar: todos os casos de seguranca sem gravacao indevida; idempotencia
concorrente em ambos os bancos; isolamento e permissao revogada; limite de custo;
retencao/exclusao verificadas; moeda/data/categoria validadas; confirmacao explicita.
Medir acerto por campo e taxa de abstencao em cada modalidade, sem usar apenas
media agregada. Conjunto pequeno de fixtures nao comprova qualidade de OCR/IA.
Produto continua manual enquanto esses bloqueios nao tiverem evidencia.
