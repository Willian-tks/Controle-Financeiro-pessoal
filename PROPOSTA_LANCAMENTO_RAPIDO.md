# DOMUS 1.5-004 — Proposta de lançamento rápido

Estado: protótipo aprovado pelo usuário em 28/09/2026 após teste. Próxima etapa: integração ao formulário real, seguida de validação funcional.

## Problema observado

O formulário atual em frontend/src/App.jsx apresenta Caixa, Competência e Compromissos, explicações operacionais e campos condicionais no mesmo bloco. A entrada cotidiana precisa destacar a compra/recebimento simples, mantendo acesso explícito aos fluxos completos.

## Fluxo proposto

1. Ação “Novo lançamento” nas telas principais, respeitando permissão do workspace.
2. Escolha explícita: Despesa, Receita ou Transferência. Não herdar silenciosamente o tipo de uma operação anterior.
3. Valor em destaque; data de hoje no fuso do usuário, visível e editável.
4. Descrição curta, conta e categoria. Categorias recentes são atalhos; sugestões não escondem o valor selecionado.
5. Forma de pagamento quando aplicável. Cartão exige escolher cartão e visualizar fatura/parcelas conforme regras existentes; transferência exige origem e destino diferentes e não apresenta categoria de despesa.
6. “Mais opções” revela observações e campos adicionais. Compromissos e demais casos não suportados pelo fluxo rápido levam ao formulário completo, preservando o rascunho e explicando o destino.
7. Botão “Salvar despesa/receita/transferência”, com conta, valor e data visíveis. Sucesso mostra confirmação e ação de novo lançamento; falha mantém o rascunho e permite corrigir. Bloquear envio duplo durante a requisição.

## Composição a prototipar

- Desktop: painel lateral com título/tipo, valor, campos principais, Mais opções e resumo antes de salvar; contexto da tela permanece visível.
- Celular: tela/painel com uma coluna, alvos de toque confortáveis, teclado decimal e ação de salvar acessível sem cobrir campos ou mensagens.
- Rótulos permanentes, foco visível, navegação por teclado e erros junto do campo. Não depender só de cor.
- Dados fictícios no protótipo; nenhuma conexão com banco ou gravação real.
- Repetir lançamento gera rascunho para revisão, nunca grava automaticamente.

## Preparação para texto, voz e imagem

Todos os modos futuros produzem o mesmo rascunho antes de gravar. A versão 1.5 não exibirá botões de microfone/câmera inoperantes.

Para foto de nota/cupom, propor captura ou seleção de imagem, prévia e extração de estabelecimento, data, moeda e total. Mostrar o documento junto dos campos extraídos para conferência. Não confundir total com subtotal, desconto ou troco; não adivinhar texto ilegível nem conta/cartão. Primeira entrega: uma despesa pelo total da compra. Itens podem auxiliar a descrição; rateio por categorias fica para escopo posterior.

Reenvio da mesma foto e compra já registrada devem gerar suspeita de duplicação, com revisão, não exclusão automática. Definir tamanho/formato, retenção, exclusão e transmissão ao provedor antes da implementação. Tratar texto da imagem como conteúdo não confiável, nunca como instrução para executar ações.

## Validação do protótipo

Comparar fluxo atual e proposto com os mesmos cenários, contando interações e observando clareza (sem alegar ganho antes de medir):

- Despesa de R$ 42,90 no débito, hoje, categoria Alimentação.
- Receita de R$ 1.500 recebida ontem.
- Transferência de R$ 200 entre contas próprias.
- Compra no cartão com identificação da fatura; compromisso futuro pelo fluxo completo.
- Valor inválido, conta ausente, falha de envio e tentativa de clique duplo.

Critério para avançar: usuário revisa e aprova o protótipo desktop/celular, com menos interações nos cenários simples e sem perder clareza de conta, data e impacto financeiro. Implementação reutiliza validações e permissões atuais; testes de cartões/transferências precedem publicação.

## Protótipo navegável

Arquivo: prototypes/lancamento-rapido.html. Executar da raiz: `python -m http.server 5175 --bind 127.0.0.1 --directory prototypes` e abrir http://127.0.0.1:5175/lancamento-rapido.html. Usa apenas dados fictícios; salvar é uma simulação. Aprovado pelo usuário após teste em 28/09/2026; integração de produção ainda pendente.

## Integração local preparada

Componente em frontend/src/QuickEntry.jsx, acionado no cabeçalho do App.jsx. Fixture do componente real em frontend/tests/quick-entry.html (apenas servidor Vite de desenvolvimento, fora do build padrão). API e persistência reais dependem de validação autenticada; produção ainda não atualizada.
