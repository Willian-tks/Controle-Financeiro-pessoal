# Runbook de Cutover - Streamlit -> FastAPI + React

Data base: 2026-02-22

## 1. Objetivo
- Publicar `api/` (FastAPI) e `frontend/` (React).
- Direcionar usuários para o novo frontend.
- Manter rollback rápido para Streamlit até estabilização.

## 2. Pré-requisitos
- Banco de produção com backup recente.
- Variáveis de ambiente definidas.
- Build frontend validado.
- Smoke backend e smoke frontend concluídos.

## 3. Variáveis de ambiente

### Backend (FastAPI)
- `DATABASE_URL`
- `JWT_SECRET` (ou equivalente já usado no projeto)
- `BRAPI_TOKEN` (se necessário para cotações)
- `CORS_ORIGINS`:
  - Exemplo: `https://seu-frontend.com,https://www.seu-frontend.com`

### Frontend (React)
- `VITE_API_BASE_URL`:
  - Exemplo: `https://sua-api.com`

## 4. Ordem de deploy
1. Publicar API FastAPI.
2. Validar API:
   - `GET /health`
   - `POST /auth/login`
   - `GET /dashboard/kpis`
   - `GET /invest/summary`
3. Publicar frontend React apontando para a API (`VITE_API_BASE_URL`).
4. Validar frontend em produção:
   - Login
   - Dashboard
   - Lançamentos
   - Investimentos (Resumo/Ativos/Operações/Proventos/Cotações)
   - Importar CSV
5. Comunicar URL nova para usuários.

## 5. Janela de corte
- Congelar mudanças no Streamlit durante a janela.
- Responsáveis:
  - Deploy API:
  - Deploy Frontend:
  - Validação funcional:
  - Decisão go/no-go:

### 5.1 Plano preenchível (usar antes do go-live)
- Data da janela: 2026-02-24 (terça-feira)
- Início (hora local): 20:00
- Fim previsto (hora local): 21:00
- Timezone: America/Sao_Paulo (UTC-03:00)
- Canal de comunicação (ex.: WhatsApp/Slack): WhatsApp (grupo projeto) + registro final no repositório

### 5.2 Responsáveis nomeados
- Deploy API (titular): Willian Cardoso
- Deploy API (backup): N/A
- Deploy Frontend (titular): Willian Cardoso
- Deploy Frontend (backup): N/A
- Validação funcional (titular): Willian Cardoso
- Validação funcional (backup): N/A
- Aprovador final go/no-go: Willian Cardoso

### 5.3 Sequência da janela (T0)
1. T-30 min: confirmar backup de banco e variáveis de ambiente.
2. T-20 min: congelar mudanças no Streamlit.
3. T-10 min: confirmar health do backend atual e status do frontend atual.
4. T0: iniciar deploy da API FastAPI.
5. T+10 min: validar `GET /health`, `POST /auth/login`, `GET /invest/summary`.
6. T+15 min: iniciar deploy do frontend React com `VITE_API_BASE_URL` final.
7. T+25 min: executar smoke funcional pós-deploy.
8. T+35 min: decisão `GO` ou `ROLLBACK`.
9. T+40 min: comunicação para usuários com status final.

### 5.4 Critérios objetivos para GO
- API responde `200` em `/health`.
- Login funcionando no frontend.
- Dashboard abre com KPIs e gráficos.
- Lançamentos cria/lista/exclui.
- Investimentos resumo exibe: `Total investido`, `Saldo na corretora`, `Retorno total`.
- Importar CSV executa prévia e importação.

### 5.5 Critérios de ROLLBACK imediato
- Erro crítico de autenticação em produção.
- Erro 5xx recorrente em endpoints principais por mais de 10 minutos.
- Inconsistência financeira grave (saldos/KPIs divergentes de forma sistêmica).
- Frontend indisponível sem recuperação rápida.

### 5.6 Registro da decisão (preencher no dia)
- Data/hora decisão: [preencher]
- Decisão final: GO / ROLLBACK
- Responsável pela decisão: [preencher]
- Evidências (links/logs/screenshots): [preencher]

## 6. Critério de Go
- Login funcional.
- Dashboard com KPIs e gráficos.
- CRUD de lançamentos funcional.
- Investimentos com Resumo funcional (`Total investido`, `Saldo na corretora`, `Retorno total`).
- Importar CSV funcional.
- Sem erro crítico 5xx na primeira bateria de testes.

## 7. Rollback rápido
1. Reapontar tráfego para o serviço Streamlit anterior.
2. Reverter variável/URL do frontend para versão anterior (se aplicável).
3. Confirmar `streamlit run app.py` operando.
4. Comunicar rollback para os usuários.

## 8. Pós-cutover (24-72h)
- Monitorar erros 4xx/5xx e latência.
- Monitorar autenticação e imports CSV.
- Conferir KPIs e valores de carteira com amostra real.
- Se estável por 72h, iniciar desativação definitiva do Streamlit.
