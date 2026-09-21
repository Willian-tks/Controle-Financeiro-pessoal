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
npm ci --include=dev --include=optional
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

### Timer de cotacoes

Para atualizar cotacoes automaticamente no VPS, copie tambem o job e o timer:

```bash
sudo cp deploy/systemd/domus-update-quotes.service /etc/systemd/system/
sudo cp deploy/systemd/domus-update-quotes.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable domus-update-quotes.timer
sudo systemctl start domus-update-quotes.timer
sudo systemctl status domus-update-quotes.timer
```

O timer foi configurado para rodar:

- segunda a sexta
- a cada 30 minutos
- das `10:05` ate `16:35`
- com uma execucao final `17:05` para consolidar o fechamento

O job roda localmente no backend, sem expor endpoint publico, e respeita por padrao a janela do mercado no fuso `America/Sao_Paulo`.

Variaveis opcionais no `.env` para ajustar a rotina:

```env
QUOTE_JOB_TZ=America/Sao_Paulo
QUOTE_JOB_START_AT=10:00
QUOTE_JOB_END_AT=17:10
QUOTE_JOB_TIMEOUT_S=25
QUOTE_JOB_MAX_WORKERS=4
QUOTE_JOB_LOCK_FILE=/tmp/domus-update-quotes.lock
```

Validacoes uteis:

```bash
systemctl list-timers | grep domus-update-quotes
sudo systemctl start domus-update-quotes.service
journalctl -u domus-update-quotes.service -n 50 --no-pager
```

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

## 8. Atualizacao de deploy — versão 1.5 em preparação

O VPS observado usa `/opt/apps/domus` e `domus-api.service`. O template
`deploy/systemd/controle-financeiro-api.service` é uma instalação alternativa,
com caminho `/var/www/controle-financeiro`: não o copie sobre o serviço existente.
Confirme `systemctl cat domus-api.service` e o caminho usado pelo Nginx antes de publicar.

### Política de dependências e build

- Node `22.12.0` e Python `3.12.4` são a referência do ambiente local desta etapa,
  registrada em `.nvmrc` e `.python-version`; a validação Linux ainda está pendente.
- Instalar o frontend com `npm ci --include=dev --include=optional`, usando o lockfile.
- `node_modules` deixa de ser versionado. Nunca copiar dependências Windows para Linux.
- O backend ainda usa intervalos em `requirements.txt`; seu congelamento reproduzível
  permanece pendente. Não tratar esses intervalos como um lockfile.
- Nesta transição, `frontend/dist` continua versionado para evitar sua remoção abrupta
  no servidor. O build gerado no Linux para o commit implantado é a referência de publicação.
- Não executar `npm ci` no ambiente local enquanto o Vite estiver em uso.

### Antes da atualização

1. Registrar o commit atual com `git rev-parse HEAD`, a unidade systemd ativa e as versões de runtime.
2. Fazer backup do frontend servido e das configurações fora do checkout.
3. Se houver mudança de banco, produzir backup consistente: SQLite via API de backup
   ou com serviço parado; PostgreSQL via ferramenta apropriada. Não copiar SQLite em escrita.
4. Inspecionar `git status --short`. Preservar alterações legítimas antes do pull;
   não usar `git reset --hard`, `git clean` ou stash indiscriminado como rotina.
5. Na primeira atualização que remove `node_modules` do Git, caches locais podem impedir
   o pull. Revisar as diferenças e preservar apenas essa pasta gerada fora do checkout
   antes da atualização; não descartar código ou configurações para resolver o conflito.

### Preparar e publicar

Execute cada etapa somente se a anterior terminar sem erro:

```bash
cd /opt/apps/domus
git pull --ff-only origin main
cd frontend
npm ci --include=dev --include=optional
VITE_API_BASE_URL= npm run build -- --outDir dist-next
```

O build é preparado em `dist-next`, sem sobrescrever o site servido durante a compilação.
Verifique o conteúdo e a ausência de URL local de API nos arquivos gerados.
Depois de preservar uma cópia do `dist` atual fora do checkout, promova o novo build
em janela controlada. A promoção automatizada/atômica será validada em etapa posterior.
Não publicar `dist-next` se o build falhar.

Após promover o build:

```bash
sudo systemctl restart domus-api.service
sudo systemctl is-active domus-api.service
curl --fail http://127.0.0.1:8000/health
sudo nginx -t
```

Recarregue o Nginx apenas se sua configuração mudou. Não é necessário reiniciar
os timers de cotações quando eles não foram alterados. Valide login, Dashboard,
Lançamentos e Investimentos pelo endereço público, incluindo atualização do navegador.

### Reversão

- Conservar o commit anterior e o backup do frontend até a validação pós-deploy.
- Em caso de falha, restaurar o artefato anterior e preparar o código do commit anterior
  em checkout controlado, preservando `.env`, dados e permissões do serviço.
- Antes de reverter backend com migração de banco, verificar compatibilidade do schema.
  Restauração de backup de dados exige avaliar lançamentos feitos após o backup.
- Reiniciar a unidade correta e repetir as verificações de saúde e navegação.
- Registrar commit, data e resultado da reversão. Este procedimento ainda exige ensaio
  em ambiente controlado antes de considerar o item 1.5-001 concluído.

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

## 11. Verificações automáticas — DOMUS CI

O workflow `.github/workflows/ci.yml` executa em pushes para `main`/`codex/**`,
PRs para `main` e por acionamento manual na aba Actions.

- `Backend tests (SQLite)`: instala `requirements-dev.txt`, executa `pip check`
  e a suíte unittest em Python definido por `.python-version`.
- `Frontend build (Linux)`: usa `.nvmrc`, instala pelo lockfile com `npm ci`,
  impede dependências instaladas versionadas e compila em `dist-next`.
- Os jobs rodam em Ubuntu 24.04, sem credenciais de produção e sem deploy.
- Cache guarda downloads de dependências; não substitui instalação limpa.
- A primeira execução remota só ocorrerá após enviar estes arquivos ao GitHub.
- Após a primeira execução aprovada, configurar os dois checks como obrigatórios
  na proteção de `main`, se disponível no repositório. O workflow sozinho não bloqueia merges/pushes.
- CI não comprova compatibilidade PostgreSQL nem valida publicação/reversão no VPS.

Referências das actions: https://github.com/actions/checkout,
https://github.com/actions/setup-node e https://github.com/actions/setup-python.
