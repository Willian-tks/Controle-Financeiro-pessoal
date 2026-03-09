# Deploy no VPS LocalWeb

Este projeto hoje roda com:

- backend FastAPI em `api.main:app`
- frontend React/Vite buildado em `frontend/dist`
- frontend e API no mesmo host, com Nginx servindo o build e fazendo proxy das rotas do backend
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
sudo mkdir -p /opt/apps/domus
sudo chown -R $USER:$USER /opt/apps/domus
```

Copie ou clone o projeto para:

```text
/opt/apps/domus
```

## 3. Backend

Criar virtualenv e instalar dependencias:

```bash
cd /opt/apps/domus
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
CORS_ORIGINS=http://SEU_IP,http://seudominio.com,https://seudominio.com
BRAPI_TOKEN=opcional
# DATABASE_URL=postgresql://usuario:senha@host:5432/banco
```

Teste manual:

```bash
. .venv/bin/activate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

## 4. Frontend

Crie ou ajuste o arquivo de producao:

```bash
cd /opt/apps/domus/frontend
printf 'VITE_API_BASE_URL=\n' > .env.production
```

Neste modelo, `VITE_API_BASE_URL` deve ficar vazio para o frontend usar a mesma origem do Nginx.

Build:

```bash
npm install
chmod +x node_modules/.bin/vite
npm run build
```

Verificacao importante:

```bash
grep -o "http://191.252.113.232:8000\|http://127.0.0.1:8000" dist/assets/index-*.js
```

O comando acima nao deve retornar nada.

O site final ficara em:

```text
/opt/apps/domus/frontend/dist
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
sudo cp deploy/nginx/controle-financeiro.conf /etc/nginx/sites-available/domus
sudo ln -s /etc/nginx/sites-available/domus /etc/nginx/sites-enabled/domus
sudo nginx -t
sudo systemctl reload nginx
```

O arquivo de Nginx deve:

- servir `frontend/dist` no `location /`
- enviar rotas como `/auth/`, `/dashboard/`, `/accounts`, `/transactions`, `/invest/` e afins para `127.0.0.1:8000`

Validacoes uteis:

```bash
curl -i http://127.0.0.1:8000/dashboard/kpis
curl -i http://SEU_IP/dashboard/kpis
nginx -T | grep -n "location /dashboard/"
```

Se o proxy estiver correto, a rota publica nao deve mais retornar HTML.

## 7. SSL

Depois que o DNS estiver apontando para o VPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

## 8. Atualizacao de deploy

Fluxo recomendado para atualizar o VPS:

```bash
cd /opt/apps/domus
git stash push -u -m "tmp-vps" # se houver alteracoes locais
git pull origin main
cd frontend
printf 'VITE_API_BASE_URL=\n' > .env.production
npm run build
sudo systemctl reload nginx
sudo systemctl restart controle-financeiro-api
```

Se `npm run build` falhar com `vite: Permission denied`:

```bash
chmod +x node_modules/.bin/vite
```

## 9. Observacoes importantes

- O `SUPER_ADMIN` e garantido no startup via bootstrap. Se `ADMIN_BOOTSTRAP_PASSWORD` estiver definido, a senha dele pode ser sobrescrita no restart.
- O `.env` local nao deve ser versionado.
- O `render.yaml` nao e usado na LocalWeb; ele pode ficar apenas como referencia historica.
- Se houver configuracoes antigas em `/etc/nginx/sites-available/default`, confirme qual arquivo esta ativo em `/etc/nginx/sites-enabled/`.

## 10. Checklist rapido

- backend responde em `127.0.0.1:8000`
- frontend buildado em `frontend/dist`
- `VITE_API_BASE_URL=` em `frontend/.env.production`
- `systemctl status controle-financeiro-api` sem erro
- `nginx -t` valido
- `curl http://SEU_IP/dashboard/kpis` responde API, nao `index.html`
- HTTPS ativo
