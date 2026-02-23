# Migracao Paralela (Sem Streamlit)

Este projeto agora tem uma base paralela:

- `api/`: backend FastAPI reutilizando a logica atual (`repo.py`, `reports.py`, `auth.py`).
- `frontend/`: app React (Vite) com login, sidebar e telas iniciais.

## 1) Rodar API

```bash
python -m pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

Endpoints principais:

- `POST /auth/login`
- `GET /me`
- `GET /accounts`
- `POST /accounts`
- `PUT /accounts/{id}`
- `DELETE /accounts/{id}`
- `GET /categories`
- `POST /categories`
- `PUT /categories/{id}`
- `DELETE /categories/{id}`
- `GET /transactions`
- `POST /transactions`
- `DELETE /transactions/{id}`
- `GET /dashboard/kpis`
- `GET /dashboard/monthly`
- `GET /dashboard/expenses-by-category`
- `GET /dashboard/account-balance`
- `GET /invest/meta`
- `GET /invest/assets`
- `POST /invest/assets`
- `PUT /invest/assets/{id}`
- `DELETE /invest/assets/{id}`
- `GET /invest/trades`
- `POST /invest/trades`
- `DELETE /invest/trades/{id}`
- `GET /invest/incomes`
- `POST /invest/incomes`
- `DELETE /invest/incomes/{id}`
- `GET /invest/prices`
- `POST /invest/prices`
- `POST /invest/prices/update-all`
- `GET /invest/portfolio`
- `POST /import/transactions-csv`
- `POST /import/assets-csv`

## 2) Rodar Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`.

## 3) Observacoes

- O Streamlit continua intacto; esta migracao e paralela.
- O frontend atual ja possui telas de `Gerenciador` (contas/categorias) e `Lançamentos` com CRUD basico.
- Dashboard completo ja migrado para React.
- Investimentos migrado no React: Ativos, Operações, Proventos, Cotações e Carteira.
- Importar CSV migrado no React (transações e ativos com prévia + importação).
- Proximo passo recomendado: refinar UX/estilo final e preparar cutover do Streamlit.
