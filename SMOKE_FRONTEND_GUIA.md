# Smoke Frontend (React) - Roteiro de Validacao

Data de referencia: 2026-02-22

## 1. Preparacao
1. Iniciar API:
```bash
uvicorn api.main:app --reload --port 8000
```
2. Iniciar frontend:
```bash
cd frontend
npm run dev
```
3. Abrir `http://127.0.0.1:5173` (ou URL exibida pelo Vite).

Credenciais bootstrap (ambiente local atual):
- Email: `willian@tks.global`
- Senha: `B3qVFb`

## 2. Criterio de aprovacao
- `OK`: fluxo executou sem erro visual e sem erro de API.
- `FALHA`: erro em tela, acao nao concluida ou dados nao atualizam.

## 3. Fluxos obrigatorios

### 3.1 Login/Logout
1. Fazer login com usuario `user` (ou usuario de teste equivalente).
2. Confirmar carregamento da sidebar e paginas.
3. Clicar em `Sair` e validar retorno para tela de login.
Resultado: `OK/FALHA`.

### 3.2 Gerenciador (contas/categorias)
1. Criar conta de teste (`SMK Conta X`).
2. Editar conta de teste (alterar nome).
3. Excluir conta de teste.
4. Criar categoria de teste (`SMK Categoria X`).
5. Editar categoria de teste.
6. Excluir categoria de teste.
Resultado: `OK/FALHA`.

### 3.3 Lancamentos (CRUD essencial)
1. Criar lancamento com conta existente.
2. Validar aparicao na tabela de recentes.
3. Excluir o lancamento criado.
Resultado: `OK/FALHA`.

### 3.4 Dashboard
1. Abrir `Dashboard` e validar KPIs renderizados.
2. Validar que os 2 graficos carregam.
3. Aplicar filtro por periodo e confirmar atualizacao.
4. Aplicar filtro por conta e confirmar atualizacao.
Resultado: `OK/FALHA`.

### 3.5 Investimentos
1. Aba `Ativos`: criar ativo de teste.
2. Aba `Operacoes`: criar operacao para o ativo.
3. Aba `Proventos`: criar provento para o ativo.
4. Aba `Cotacoes`: salvar cotacao manual.
5. Aba `Resumo`: validar cards e tabela de carteira.
Resultado: `OK/FALHA`.

### 3.6 Importar CSV
1. Subir CSV de transacoes para `Previa`.
2. Confirmar preview renderizada.
3. Executar `Importar transacoes`.
4. Repetir para ativos (preview + import).
Resultado: `OK/FALHA`.

## 4. Evidencias minimas
- 1 screenshot por pagina: `Gerenciador`, `Lancamentos`, `Dashboard`, `Investimentos`, `Importar CSV`.
- 1 screenshot do login e 1 do logout.
- Anotar qualquer erro exibido em tela.

## 5. Registro final
Preencha ao final:
- Login/Logout:
- Gerenciador:
- Lancamentos:
- Dashboard:
- Investimentos:
- Importar CSV:
- Observacoes:
