# DOMUS — Preparação de release 1.5

Estado em 26/10/2026: candidata local **1.5.0-rc.1**, não publicada.
Este documento não autoriza deploy. A versão final 1.5.0 não está liberada.

Autorização posterior, em 26/10/2026: usuário autorizou validar e publicar a
candidata, com adiamento explícito da conciliação das operações 85–88.
Preservar esses dados e suas limitações de custo/rentabilidade; o adiamento não
encerra o 002 nem autoriza reparo. CI e smoke real do VPS continuam obrigatórios.

## Identidade e rastreabilidade

frontend/src/productVersion.json é a fonte da versão; product_version.py
reutiliza o valor para FastAPI. package.json e package-lock.json devem coincidir.
O selo da aplicação identifica a candidata, não o commit nem a data implantada.
Antes do build de release, exigir checkout limpo e registrar SHA completo aprovado.
O HEAD local de base é 26b748a; existem mudanças não commitadas, portanto ele
NÃO identifica esta candidata. Preencher o registro abaixo após commit/deploy.

| Evidência | Valor |
|---|---|
| Versão preparada | 1.5.0-rc.1 |
| Commit aprovado no CI | Pendente |
| Tag | Não criada |
| Data/hora e fuso da implantação | Pendente |
| Commit anterior no VPS | Confirmar antes de atualizar |
| Backup de banco/configurações | Pendente, registrar local e teste de leitura |
| Backup do frontend | Registrar caminho retornado pela promoção |
| Backend/ambiente anterior | Registrar SHA e caminho do ambiente preservado |
| Responsável e validação funcional | Pendente |

## Bloqueios antes de liberar

- [ ] Revisar/commitar o lote sem arquivos temporários, credenciais ou dados locais.
- [ ] Aprovar funcionalmente o fechamento do 007 (fonte/data/moeda/cache/falhas).
- [x] Decidir explicitamente as exceções legadas do 002: conciliar ou registrar
  adiamento aceito com limitações conhecidas. Não alterar operações 85–88.
- [x] Revisar o contrato do 009; preparação não comprova qualidade de modelo.
- [ ] Aprovar todos os checks CI do SHA exato: SQLite, PostgreSQL e frontend.
- [ ] Confirmar janela, acesso, backup, commit atual e plano de reversão no VPS.

## Evidências locais

- Etapa 007: 103 testes Python; 008: 22 testes Node e build Vite aprovados,
  conforme registros do backlog. Não substituem nova execução no SHA final.
- Etapa 009: 5 testes de integridade para 18 cenários e 3 SVGs sintéticos.
  Nenhum modelo/OCR foi executado.
- Etapa 010: 109 testes Python, 22 testes Node e build Vite aprovados localmente
  em 26/10/2026; identificação candidata conferida na interface autenticada.
  A suíte Python foi repetida fora do sandbox após restrições de temporários.
  A API local sem autoreload precisa ser reiniciada para novos metadados.
- PostgreSQL local indisponível: a validação dessa plataforma depende do CI.

## Atualização controlada

Seguir VPS_LOCALWEB_DEPLOY.md, preservando .env, banco e ambiente ativo.
Não executar git reset, limpeza de backups ou stash indiscriminado no servidor.
Se git status indicar frontend/dist alterado, preservar a versão servida e
resolver somente o artefato gerado conforme o guia antes do pull; não descartar
arquivos de aplicação/configuração para forçar atualização.

Depois dos bloqueios: preparar checkout e dependências no SHA aprovado, gerar
frontend/dist-next com VITE_API_BASE_URL vazio no VPS e promover pelo utilitário
deploy/frontend_release.py, anotando dist-backup retornado. Reiniciar a API com
o serviço já configurado e validar saúde/Nginx/HTTPS. Confirmar versão em tela
e metadados OpenAPI da API. Não copiar node_modules do Windows.

Esta etapa de identificação não adiciona migração de banco nem dependências.
O lote acumulado também muda backend/cotações: somente rebuild do frontend
não publica o conjunto. Copiar também product_version.py e o JSON de versão.

## Smoke após publicação

- [ ] Login, workspace correto e permissões de leitura/inclusão.
- [ ] Dashboard: totais/filtros/drill-down conferem com detalhamento.
- [ ] Lançamentos: despesa/receita/transferência; cartão e compromisso.
- [ ] Investimentos: BRL/USD, custo/mercado, origem/moeda/data e cotação em cache.
- [ ] Falha de provedor sem falso sucesso; carteira abre sem dependência de rede.
- [ ] Layout móvel sem ações ocultas, erros locais legíveis e versão candidata.
- [ ] Listas e demais cadastros carregam; usuário sem permissão não grava.

Usar dados descartáveis identificados, com autorização, e conferir sua remoção;
não criar operações fictícias em contas reais para testar números.

## Reversão

Parar a publicação em caso de falha e registrar etapa/erro. O utilitário de
frontend reverte pelo nome real do dist-backup preservado (seção 12 do guia);
não reverter apenas frontend se o problema for backend.
Backend: restaurar o código do SHA anterior e o ambiente Python preservado pelo
procedimento operacional, mantendo configurações; reiniciar e repetir smoke.
Não presumir que git pull inverso restaura banco. Antes de qualquer restauração
de banco, avaliar gravações após deploy, compatibilidade e perda de dados,
obter autorização explícita e backup atual. Nenhuma restauração automática.

## Encerramento

Registrar SHA, versão, data, backups e confirmação real de funcionamento no VPS.
Somente então encerrar a publicação correspondente no backlog.
Para promover a 1.5.0 final: resolver ou adiar explicitamente os bloqueios,
alinhar a identidade (retirar sufixo/selo de candidata), repetir CI e publicar
tag v1.5.0 no commit efetivamente liberado. Não rotular a candidata como final.
