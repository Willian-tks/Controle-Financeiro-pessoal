# Deploy no VPS LocalWeb

Este projeto hoje roda com:

- backend FastAPI em `api.main:app`
- frontend React/Vite buildado em `frontend/dist`
- banco SQLite por padrao, com suporte a PostgreSQL via `DATABASE_URL`

## 1. Preparar o servidor

Instale os pacotes base no VPS Linux:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx nodejs npm
```

Se for usar PostgreSQL no VPS ou externo, configure `DATABASE_URL`. Sem isso, a aplicacao usa SQLite em `data/finance.db`.

## 2. Publicar o projeto

Exemplo de estrutura:

```bash
sudo mkdir -p /var/www/controle-financeiro
sudo chown -R $USER:$USER /var/www/controle-financeiro
```

Copie o projeto para:

```text
/var/www/controle-financeiro
```

## 3. Backend

Criar virtualenv e instalar dependencias:

```bash
cd /var/www/controle-financeiro
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Criar `.env` a partir de `.env.example`.

Variaveis minimas recomendadas:

```env
JWT_SECRET=troque-para-um-segredo-forte
ADMIN_BOOTSTRAP_EMAIL=admin@seudominio.com
ADMIN_BOOTSTRAP_PASSWORD=troque-esta-senha
ADMIN_BOOTSTRAP_NAME=Super Admin
CORS_ORIGINS=https://app.seudominio.com,https://www.app.seudominio.com
BRAPI_TOKEN=opcional
# DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

Teste manual:

```bash
. .venv/bin/activate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

## 4. Frontend

Crie o arquivo de producao:

```bash
cd /var/www/controle-financeiro/frontend
cp .env.production.example .env.production
```

Ajuste:

```env
VITE_API_BASE_URL=https://api.seudominio.com
```

Build:

```bash
npm install
npm run build
```

O site final ficara em:

```text
/var/www/controle-financeiro/frontend/dist
```

## 5. systemd

Copie o service:

```bash
sudo cp deploy/systemd/controle-financeiro-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable controle-financeiro-api
sudo systemctl start controle-financeiro-api
sudo systemctl status controle-financeiro-api
```

Se o usuario de execucao nao for `www-data`, ajuste o arquivo do service antes.

## 6. Nginx

Copie a configuracao:

```bash
sudo cp deploy/nginx/controle-financeiro.conf /etc/nginx/sites-available/controle-financeiro
sudo ln -s /etc/nginx/sites-available/controle-financeiro /etc/nginx/sites-enabled/controle-financeiro
sudo nginx -t
sudo systemctl reload nginx
```

Troque os dominios:

- `app.seudominio.com`
- `www.app.seudominio.com`
- `api.seudominio.com`

## 7. SSL

Depois que o DNS estiver apontando para o VPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

## 8. Observacoes importantes

- O `SUPER_ADMIN` e garantido no startup via bootstrap. Se `ADMIN_BOOTSTRAP_PASSWORD` estiver definido, a senha dele pode ser sobrescrita no restart.
- O `.env` local nao deve ser versionado.
- O `render.yaml` nao e usado na LocalWeb; ele pode ficar apenas como referencia historica.
- Se quiser reduzir risco em producao, o proximo ajuste correto e mudar o bootstrap para criar o admin apenas se ele nao existir.

## 9. Checklist rapido

- backend responde em `127.0.0.1:8000`
- frontend buildado em `frontend/dist`
- `VITE_API_BASE_URL` aponta para o dominio da API
- `CORS_ORIGINS` inclui o dominio do frontend
- `systemctl status controle-financeiro-api` sem erro
- `nginx -t` valido
- HTTPS ativo
