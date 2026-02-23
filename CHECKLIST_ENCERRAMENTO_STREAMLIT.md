# Checklist de Encerramento do Streamlit

## 1. Paridade funcional (bloqueante)
- [x] Login/logout no React + API funcionando para perfil `user`.
- [x] Página `Gerenciador` cobre contas/categorias (criar, editar, excluir).
- [x] Página `Lançamentos` cobre CRUD essencial (criar, listar, excluir).
- [x] Página `Dashboard` exibe KPIs, gráficos e tabelas com filtros por período/conta.
- [x] Página `Investimentos` cobre ativos, operações, proventos, cotações e carteira.
- [x] Página `Importar CSV` cobre preview + importação de transações e ativos.
- [x] Feedback de erro/sucesso visível em todas as ações críticas.

## 2. Dados e consistência (bloqueante)
- [ ] Banco em ambiente alvo com backup atualizado antes do corte.
- [ ] Validação de contagem (amostra): contas, categorias, lançamentos, ativos, operações e proventos.
- [ ] Validação financeira (amostra): KPIs e saldos batem entre Streamlit e React/API.
- [ ] Timezone e formato de data confirmados (`YYYY-MM-DD`) em toda API.
- [x] Importação CSV validada com arquivo real (preview + import final).

## 3. Qualidade técnica (bloqueante)
- [x] Build frontend sem erro (`npm run build`).
- [x] Smoke backend sem erro (`/health`, auth, CRUDs principais).
- [x] Smoke frontend sem erro (navegação entre páginas + ações principais). Ver roteiro em `SMOKE_FRONTEND_GUIA.md`.
- [ ] Logs backend sem exceções recorrentes em uso normal.
- [x] CORS e variáveis de ambiente revisados para produção.

## 4. Deploy e operação (bloqueante)
- [ ] Frontend publicado com URL final.
- [ ] Backend publicado com URL final e banco correto.
- [x] Variáveis `API_BASE_URL` (frontend), CORS e credenciais revisadas.
- [ ] Monitoramento mínimo ativo (healthcheck + erro de API).
- [x] Plano de rollback documentado e testado (reativar Streamlit rapidamente). Ver `RUNBOOK_CUTOVER_STREAMLIT.md`.

## 5. Go-live
- [ ] Janela de corte definida (data/hora + responsáveis).
- [ ] Congelamento de mudanças no Streamlit durante o corte.
- [ ] Publicação React/API em produção.
- [ ] Teste pós-corte de ponta a ponta com usuário real.
- [ ] Comunicação para usuários: novo endereço + mudanças principais.

## 6. Pós-corte (24-72h)
- [ ] Monitorar erros 4xx/5xx e desempenho (latência endpoints principais).
- [ ] Corrigir regressões críticas detectadas na operação real.
- [ ] Validar novamente KPIs e carteira em base produtiva.
- [ ] Confirmar estabilidade por 2-3 dias.

## 7. Encerramento definitivo do Streamlit
- [ ] Remover rota/processo de execução do Streamlit em produção.
- [ ] Arquivar `app.py`/componentes legados como histórico (sem uso ativo).
- [ ] Atualizar documentação oficial para React + API.
- [ ] Registrar versão final de corte (tag/release).
- [ ] Fechar item de migração como concluído no repositório.

---

## Execução realizada (2026-02-22)
- Build frontend executado com sucesso em `frontend/` via `npm run build`.
- Smoke backend executado com sucesso em `http://127.0.0.1:8000`:
  - `GET /health`
  - `POST /auth/login`
  - `GET /me`
  - `GET /dashboard/kpis`, `GET /dashboard/monthly`, `GET /dashboard/expenses-by-category`, `GET /dashboard/account-balance`
  - `GET /invest/meta`, `GET /invest/assets`, `GET /invest/trades`, `GET /invest/incomes`, `GET /invest/prices`, `GET /invest/portfolio`
- Importação CSV validada com arquivo temporário real:
  - `POST /import/transactions-csv` com `preview_only=true`
  - `POST /import/transactions-csv` com `preview_only=false`
- Observação: itens de `Smoke frontend`, `Deploy`, `Go-live` e `Pós-corte` exigem validação operacional/manual no ambiente alvo.

## Execução visual (2026-02-22)
- `Login/Logout`: OK.
- `Gerenciador`: OK (criar/editar/excluir conta e categoria).
- `Lançamentos`: OK (criar/listar/excluir).
- `Dashboard`: KPIs, gráficos e filtros OK.
- `Investimentos`: OK (abas e renderização).
- `Importar CSV`: OK (seleção, prévia, importação e mensagem de sucesso).
