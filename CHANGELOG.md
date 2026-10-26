# Changelog

## 1.5.0-rc.1 — candidata local, 2026-10-26

Não publicada. Parte das mudanças já chegou à produção em lotes anteriores;
consultar Backlog1.5.md para evidências por item. Nenhuma tag final criada.

- Lançamento rápido com despesa, receita e transferência; cartão e compromisso
  continuam no formulário completo, preservando seleções.
- Dashboard distingue saldo, resultado, compromissos e patrimônio.
- Rótulos, mensagens, foco e comportamento móvel dos formulários padronizados.
- Cotações com fonte, data, moeda e falhas explícitas; cache com TTL e indicação
  de referência reaproveitada, sem fingir nova consulta ao provedor.
- Carteira identifica custo médio, valor manual e motor de rentabilidade.
- Indicadores e relatório de cotações separados da orquestração da interface;
  formatação compartilhada com testes de contrato.
- Contrato de rascunho assistido e corpus sintético preparados. IA, OCR,
  transcrição e cobrança de provedor não estão ativos.
- Versão candidata alinhada entre interface, manifesto e metadados da API.

### Pendências e exclusões

- 002: quatro operações legadas a preço zero (85–88), preservadas até decisão;
  não houve conciliação integral nem autorização para reparo automático.
- Em 26/10/2026, usuário autorizou publicar a candidata adiando explicitamente
  essa conciliação; custos/rentabilidade desses ativos continuam com limitação.
- 007: aprovação funcional do fechamento e validação após deploy pendentes.
- CI do commit final, publicação e confirmação funcional no VPS pendentes.
- Time Deposit, favoritos adicionais e ativação de IA não fazem parte deste lote.

Instruções e critérios de liberação em RELEASE_1.5.md e VPS_LOCALWEB_DEPLOY.md.
