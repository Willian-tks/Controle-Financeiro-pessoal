# app.py

import os
import certifi

# força certificados SSL (resolve curl(77))
ca = certifi.where()
os.environ["SSL_CERT_FILE"] = ca
os.environ["REQUESTS_CA_BUNDLE"] = ca
os.environ["CURL_CA_BUNDLE"] = ca  # <<< ESTE é o que resolve o curl(77) na maioria dos casos
os.environ["BRAPI_TOKEN"] = "u7tTrWyF5sCyR5gtLkQqJd"

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

from db import init_db, DB_PATH, USE_POSTGRES
import repo
import reports
from utils import to_brl, normalize_import_df
from utils import card, end_card, badge

import invest_repo
import invest_reports
import invest_quotes

def inject_corporate_css():
    st.markdown("""
    <style>
      /* Layout geral */
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1180px; }
      section[data-testid="stSidebar"] { border-right: 1px solid #e5e7eb; }
      hr { margin: 1.2rem 0; }

      /* Tipografia */
      h1, h2, h3 { letter-spacing: -0.02em; }
      h1 { font-weight: 750; }
      h2, h3 { font-weight: 700; }
      p, li, label, div { color: #111827; }

      /* Cards */
      .card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 10px 26px rgba(17,24,39,0.06);
        margin-bottom: 14px;
      }
      .card-title {
        font-weight: 700;
        margin: 0 0 8px 0;
      }
      .muted { color: #6b7280; }

      /* Badges */
      .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 650;
        border: 1px solid #e5e7eb;
        background: #f9fafb;
        color: #111827;
      }
      .badge-ok { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
      .badge-warn { background: #fffbeb; border-color: #fde68a; color: #92400e; }
      .badge-bad { background: #fef2f2; border-color: #fecaca; color: #991b1b; }

      /* Botões */
      div.stButton > button {
        border-radius: 12px !important;
        padding: 0.55rem 1rem !important;
        font-weight: 650 !important;
        border: 1px solid #d1d5db !important;
      }

      /* Inputs */
      div[data-baseweb="input"] input, textarea {
        border-radius: 12px !important;
      }
      div[data-baseweb="select"] > div {
        border-radius: 12px !important;
      }

      /* DataFrame */
      div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
      }

      /* Alertas (deixa mais corporativo) */
      div[data-testid="stAlert"] {
        border-radius: 14px;
        border: 1px solid #e5e7eb;
      }
    </style>
    """, unsafe_allow_html=True)

inject_corporate_css()


# ----------------------------
# Config
# ----------------------------
st.set_page_config(page_title="Financeiro Pessoal", layout="wide")
st.title("Controle Financeiro Pessoal (MVP)")

st.caption(f"CWD: {os.getcwd()}")
if USE_POSTGRES:
    st.caption("DB: PostgreSQL (via DATABASE_URL)")
else:
    st.caption(f"DB_PATH: {DB_PATH}")

init_db()


# ----------------------------
# Helpers: sempre ter mapas (evita NameError)
# ----------------------------
def load_accounts_categories():
    accounts_ = repo.list_accounts() or []
    categories_ = repo.list_categories() or []

    acc_map_ = {r["name"]: r["id"] for r in accounts_}
    acc_type_map = {r["name"]: r["type"] for r in accounts_}
    cat_map_ = {r["name"]: r["id"] for r in categories_}
    cat_kind_map_ = {r["name"]: r["kind"] for r in categories_}

    return accounts_, categories_, acc_map_, acc_type_map, cat_map_, cat_kind_map_


accounts, categories, acc_map,acc_type_map, cat_map, cat_kind_map = load_accounts_categories()


# =========================================================
# Sidebar - Cadastros
# =========================================================
st.sidebar.header("Cadastros")
cad_tab1, cad_tab2 = st.sidebar.tabs(["Contas", "Categorias"])

# --------- CONTAS ----------
with cad_tab1:
    st.markdown("### Nova conta")
    acc_name = st.text_input("Nome da conta", key="acc_name_new")
    acc_type = st.selectbox("Tipo", ["Banco", "Cartao", "Dinheiro", "Corretora"], key="acc_type_new")

    if st.button("Salvar conta", key="btn_save_acc"):
        if acc_name.strip():
            repo.create_account(acc_name.strip(), acc_type)
            st.success("Conta salva.")
            st.rerun()
        else:
            st.warning("Informe um nome.")

    st.divider()
    st.markdown("### Gerenciar contas")

    accounts_list = repo.list_accounts() or []
    if not accounts_list:
        st.info("Nenhuma conta cadastrada.")
    else:
        acc_names = [f'{r["id"]} - {r["name"]} ({r["type"]})' for r in accounts_list]
        acc_pick = st.selectbox("Selecione", acc_names, key="acc_pick")

        acc_id = int(acc_pick.split(" - ")[0])  
        acc_row = next(r for r in accounts_list if int(r["id"]) == acc_id)

        new_name = st.text_input("Editar nome", value=acc_row["name"], key="acc_edit_name")
        new_type = st.selectbox(
            "Editar tipo",
            ["Banco", "Cartao", "Dinheiro", "Corretora"],
            index=["Banco", "Cartao", "Dinheiro", "Corretora"].index(acc_row["type"]),
            key="acc_edit_type"
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Atualizar conta", key="btn_upd_acc"):
                if not new_name.strip():
                    st.warning("Nome não pode ser vazio.")
                else:
                    repo.update_account(acc_id, new_name.strip(), new_type)
                    st.success("Conta atualizada.")
                    st.rerun()

        with c2:
            used = repo.account_usage_count(acc_id)
            if st.button("Excluir conta", key="btn_del_acc"):
                if used > 0:
                    st.warning(f"Não pode excluir: {used} lançamento(s) usam esta conta.")
                else:
                    deleted = repo.delete_account(acc_id)
                    if deleted:
                        st.success("Conta excluída.")
                        st.rerun()
                    else:
                        st.warning("Não foi possível excluir (talvez já tenha sido removida).")

# --------- CATEGORIAS ----------
with cad_tab2:
    st.markdown("### Nova categoria")
    cat_name = st.text_input("Nome da categoria", key="cat_name_new")
    cat_kind = st.selectbox("Tipo", ["Despesa", "Receita", "Transferencia"], key="cat_kind_new")

    if st.button("Salvar categoria", key="btn_save_cat"):
        if cat_name.strip():
            repo.create_category(cat_name.strip(), cat_kind)
            st.success("Categoria salva.")
            st.rerun()
        else:
            st.warning("Informe um nome.")

    st.divider()
    st.markdown("### Gerenciar categorias")

    categories_list = repo.list_categories() or []
    if not categories_list:
        st.info("Nenhuma categoria cadastrada.")
    else:
        cat_names = [f'{r["id"]} - {r["name"]} ({r["kind"]})' for r in categories_list]
        cat_pick = st.selectbox("Selecione", cat_names, key="cat_pick")

        cat_id = int(cat_pick.split(" - ")[0])
        cat_row = next(r for r in categories_list if int(r["id"]) == cat_id)

        new_cat_name = st.text_input("Editar nome", value=cat_row["name"], key="cat_edit_name")
        new_kind = st.selectbox(
            "Editar tipo",
            ["Despesa", "Receita", "Transferencia"],
            index=["Despesa", "Receita", "Transferencia"].index(cat_row["kind"]),
            key="cat_edit_kind"
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Atualizar categoria", key="btn_upd_cat"):
                if not new_cat_name.strip():
                    st.warning("Nome não pode ser vazio.")
                else:
                    repo.update_category(cat_id, new_cat_name.strip(), new_kind)
                    st.success("Categoria atualizada.")
                    st.rerun()

        with c2:
            used = repo.category_usage_count(cat_id)
            if st.button("Excluir categoria", key="btn_del_cat"):
                if used > 0:
                    st.warning(f"Não pode excluir: {used} lançamento(s) usam esta categoria.")
                else:
                    deleted = repo.delete_category(cat_id)
                    if deleted:
                        st.success("Categoria excluída.")
                        st.rerun()
                    else:
                        st.warning("Não foi possível excluir (talvez já tenha sido removida).")


st.sidebar.divider()
st.sidebar.subheader("Limpeza de dados (TESTES)")

st.sidebar.caption(
    "Use apenas em ambiente de testes.\n"
    "Digite LIMPAR para habilitar os botões."
)

confirm = st.sidebar.text_input(
    'Confirmação',
    placeholder='Digite LIMPAR',
    key="confirm_clear"
)

c1, c2 = st.sidebar.columns(2)
c3, c4 = st.sidebar.columns(2)

with c1:
    if st.button("Lançamentos", disabled=(confirm != "LIMPAR")):
        n = repo.clear_transactions()
        st.sidebar.success(f"{n} lançamentos removidos")
        st.rerun()

with c2:
    if st.button("Mov. Invest.", disabled=(confirm != "LIMPAR")):
        res = invest_repo.clear_invest_movements()
        st.sidebar.success(
            f"Trades: {res['trades']} | "
            f"Proventos: {res['income_events']} | "
            f"Cotações: {res['prices']}"
        )
        st.rerun()

with c3:
    if st.button("Ativos", disabled=(confirm != "LIMPAR")):
        try:
            n = invest_repo.clear_assets()
            st.sidebar.success(f"{n} ativos removidos")
            st.rerun()
        except Exception as e:
            st.sidebar.error(
                "Erro ao remover ativos.\n"
                "Limpe primeiro trades, proventos e cotações."
            )

with c4:
    if st.button("RESET TOTAL", disabled=(confirm != "LIMPAR")):
        repo.clear_transactions()
        invest_repo.clear_invest_movements()
        invest_repo.clear_assets()
        st.sidebar.success("Base de investimentos zerada.")
        st.rerun()
# Recarrega mapas (pois sidebar pode ter alterado)
accounts, categories, acc_map, acc_type_map, cat_map, cat_kind_map = load_accounts_categories()


# =========================================================
# Tabs principais
# =========================================================
tab0, tab1, tab2, tab3, tab4 = st.tabs(["Contas", "Lançamentos", "Dashboard", "Importar CSV", "Investimentos"])

# ========== TAB 0: Contas (Saldos) ==========
with tab0:
    st.subheader("Saldos das contas")

    df_all = reports.df_transactions()

    ab = reports.account_balance(df_all)

    if ab.empty:
        st.info("Sem lançamentos ainda.")
    else:
        ab_show = ab.copy()
        ab_show["saldo_brl"] = ab_show["saldo"].apply(to_brl)

        st.dataframe(
            ab_show[["account", "saldo_brl"]],
            use_container_width=True,
            hide_index=True
        )

        total = float(ab_show["saldo"].sum())
        st.metric("Saldo total (somando todas as contas)", to_brl(total))


# =========================================================
# TAB 1: Lançamentos
# =========================================================
with tab1:
    st.subheader("Novo lançamento")

    col1, col2, col3, col4 = st.columns([1.2, 2.5, 1.2, 1.2])
    with col1:
        date = st.date_input("Data", key="tx_date")
    with col2:
        desc = st.text_input("Descrição", key="tx_desc")
    with col3:
        amount_abs = st.number_input(
            "Valor", min_value=0.0, value=0.0, step=10.0, format="%.2f", key="tx_amount"
        )
    with col4:
        account_name = st.selectbox(
            "Conta",
            list(acc_map.keys()) if acc_map else ["(cadastre uma conta)"],
            key="tx_account"
        )

    col5, col6, col7 = st.columns([1.2, 1.2, 2.0])
    with col5:
        category_name = st.selectbox(
            "Categoria (opcional)",
            ["(sem)"] + list(cat_map.keys()),
            key="tx_category"
        )
    with col6:
        method = st.text_input("Método (opcional)", placeholder="Pix, Débito, Crédito...", key="tx_method")
    with col7:
        notes = st.text_input("Obs (opcional)", key="tx_notes")

    # ---------- (A) Detecta o tipo da categoria selecionada ----------
    kind = cat_kind_map.get(category_name) if category_name != "(sem)" else None

    # ---------- (B) Se for Transferência, mostra a Conta Origem ----------
    source_account_name = None
    if kind == "Transferencia":
        # garante que exista acc_type_map no app.py (mapa nome -> tipo)
        # acc_type_map = {r["name"]: r["type"] for r in accounts}
        non_broker_accounts = [n for n in acc_map.keys() if acc_type_map.get(n) != "Corretora"]

        source_account_name = st.selectbox(
            "Conta origem (Transferência)",
            ["(selecione)"] + non_broker_accounts,
            key="tx_source_account"
        )

    if st.button("Salvar lançamento", type="primary", key="btn_save_tx"):
        if not acc_map:
            st.error("Cadastre uma conta antes.")
            st.stop()

        if not desc.strip():
            st.error("Informe a descrição.")
            st.stop()

        account_id = acc_map.get(account_name)  # DESTINO
        category_id = None if category_name == "(sem)" else cat_map.get(category_name)
        amount = float(amount_abs)

        # -------------------------
        # TRANSFERENCIA (2 lançamentos)
        # -------------------------
        if kind == "Transferencia":
            if not source_account_name or source_account_name == "(selecione)":
                st.error("Selecione a conta ORIGEM da transferência.")
                st.stop()

            if source_account_name == account_name:
                st.error("Conta origem e destino não podem ser a mesma.")
                st.stop()

            # destino precisa ser corretora
            if acc_type_map.get(account_name) != "Corretora":
                st.error("Para Transferência, a conta DESTINO precisa ser do tipo Corretora.")
                st.stop()

            # origem não pode ser corretora
            if acc_type_map.get(source_account_name) == "Corretora":
                st.error("A conta ORIGEM não pode ser Corretora.")
                st.stop()

            source_account_id = acc_map[source_account_name]

            # saldo da origem (somatório dos lançamentos dessa conta)
            df_all = reports.df_transactions()
            if df_all.empty:
                source_balance = 0.0
            else:
                source_balance = float(df_all[df_all["account"] == source_account_name]["amount_brl"].sum())

            if source_balance < amount:
                st.error(
                    f"Saldo insuficiente na conta origem ({to_brl(source_balance)}). "
                    f"Precisa de {to_brl(amount)}."
                )
                st.stop()

            # 1) débito na origem
            repo.insert_transaction(
                date=date.strftime("%Y-%m-%d"),
                description=f"TRANSF -> {account_name} | {desc.strip()}",
                amount=-abs(amount),
                account_id=source_account_id,
                category_id=category_id,
                method=method.strip() if method.strip() else None,
                notes=notes.strip() if notes.strip() else None
            )

            # 2) crédito no destino (corretora)
            repo.insert_transaction(
                date=date.strftime("%Y-%m-%d"),
                description=f"TRANSF <- {source_account_name} | {desc.strip()}",
                amount=abs(amount),
                account_id=account_id,
                category_id=category_id,
                method=method.strip() if method.strip() else None,
                notes=notes.strip() if notes.strip() else None
            )

            st.success("Transferência registrada (origem debitada e corretora creditada).")
            st.rerun()

        # -------------------------
        # DESPESA / RECEITA / (sem)
        # -------------------------
        amount_signed = abs(amount)
        if kind == "Despesa":
            amount_signed = -abs(amount_signed)

        repo.insert_transaction(
            date=date.strftime("%Y-%m-%d"),
            description=desc.strip(),
            amount=amount_signed,
            account_id=account_id,
            category_id=category_id,
            method=method.strip() if method.strip() else None,
            notes=notes.strip() if notes.strip() else None
        )

        st.success("Lançamento salvo.")
        st.rerun()

    st.divider()
    st.subheader("Lançamentos recentes")

    df_tx = reports.df_transactions()
    if df_tx.empty:
        st.info("Sem lançamentos ainda.")
    else:
        show = df_tx.sort_values("date", ascending=False).head(50).copy()
        show["date"] = show["date"].dt.strftime("%Y-%m-%d")
        show["amount_brl"] = show["amount_brl"].apply(to_brl)

        st.dataframe(
            show[["id", "date", "description", "account", "category", "amount_brl"]],
            use_container_width=True,
            hide_index=True
        )

        col_del, col_btn = st.columns([1.2, 1.0])
        with col_del:
            del_id = st.number_input("Excluir lançamento por ID", min_value=0, step=1, value=0, key="tx_del_id")
        with col_btn:
            if st.button("Excluir", key="btn_del_tx"):
                if del_id > 0:
                    repo.delete_transaction(int(del_id))
                    st.success("Excluído (se existia).")
                    st.rerun()
                else:
                    st.warning("Informe um ID > 0.")


# =========================================================
# TAB 2: Dashboard (tudo aqui dentro!)
# =========================================================
with tab2:
    st.subheader("Filtros")

    f1, f2, f3 = st.columns([1.2, 1.2, 2.0])
    with f1:
        date_from = st.date_input("De", value=None, key="dash_date_from")
    with f2:
        date_to = st.date_input("Até", value=None, key="dash_date_to")
    with f3:
        acc_filter = st.selectbox("Conta", ["(todas)"] + list(acc_map.keys()), key="dash_acc_filter")

    df = reports.df_transactions(
        date_from.strftime("%Y-%m-%d") if date_from else None,
        date_to.strftime("%Y-%m-%d") if date_to else None
    )
    if acc_filter != "(todas)" and not df.empty:
        df = df[df["account"] == acc_filter]

    k = reports.kpis(df)
    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas", to_brl(k["receitas"]))
    k2.metric("Despesas", to_brl(k["despesas"]))
    k3.metric("Saldo", to_brl(k["saldo"]))

    st.divider()

    st.markdown("## Resumo financeiro do período")

    # 1) Saldo por mês (gráfico)
    st.markdown("### Saldo por mês")
    ms = reports.monthly_summary(df)
    if ms.empty:
        st.info("Sem dados para o período.")
    else:
        ms_plot = ms.copy()
        ms_plot["month"] = pd.to_datetime(ms_plot["month"].astype(str) + "-01", errors="coerce")
        fig = px.line(ms_plot, x="month", y="saldo", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        # 2) Resumo mensal (tabela) -> abaixo do gráfico
        st.markdown("### Resumo mensal")
        ms_fmt = ms.copy()
        ms_fmt["receitas"] = ms_fmt["receitas"].apply(to_brl)
        ms_fmt["despesas"] = ms_fmt["despesas"].apply(to_brl)
        ms_fmt["saldo"] = ms_fmt["saldo"].apply(to_brl)
        st.dataframe(ms_fmt, use_container_width=True, hide_index=True)

    st.divider()

    # 3) Despesas por categoria
    st.markdown("### Despesas por categoria")
    ce = reports.category_expenses(df)
    if ce.empty:
        st.info("Sem despesas no período.")
    else:
        fig2 = px.bar(ce.head(15), x="valor", y="category", orientation="h")
        st.plotly_chart(fig2, use_container_width=True)

    # 4) Saldo por conta
    st.markdown("### Saldo por conta")
    ab = reports.account_balance(df)
    if ab.empty:
        st.info("Sem dados.")
    else:
        ab_fmt = ab.copy()
        ab_fmt["saldo"] = ab_fmt["saldo"].apply(to_brl)
        st.dataframe(ab_fmt, use_container_width=True, hide_index=True)

    st.divider()

    # 5) Patrimônio (expander)
    with st.expander("Patrimônio (por dia) - abrir", expanded=False):
        st.caption(
            "Depende de cotações salvas. Dias sem cotação podem aparecer zerados e gerar saltos - normal com poucos dados."
        )

        if not date_from or not date_to:
            end = pd.Timestamp.today().normalize()
            start = end - pd.Timedelta(days=90)
            d_from = start.strftime("%Y-%m-%d")
            d_to = end.strftime("%Y-%m-%d")
        else:
            d_from = date_from.strftime("%Y-%m-%d")
            d_to = date_to.strftime("%Y-%m-%d")

        cash_ts = reports.cash_balance_timeseries(d_from, d_to)
        inv_ts = invest_reports.investments_value_timeseries(d_from, d_to)

        if inv_ts.empty and cash_ts.empty:
            st.info("Sem dados suficientes para patrimônio ainda.")
        else:
            if inv_ts.empty:
                base = cash_ts.copy()
                base["invest_market_value"] = 0.0
            elif cash_ts.empty:
                base = inv_ts.copy()
                base["cash_balance"] = 0.0
            else:
                base = pd.merge(inv_ts, cash_ts, on="date", how="outer").sort_values("date")

            base["cash_balance"] = base.get("cash_balance", 0.0)
            base["cash_balance"] = base["cash_balance"].fillna(method="ffill").fillna(0.0)

            if "invest_market_value" not in base.columns:
                base["invest_market_value"] = 0.0
            base["invest_market_value"] = base["invest_market_value"].fillna(0.0)

            base["net_worth"] = base["cash_balance"] + base["invest_market_value"]

            fignw = px.line(base, x="date", y="net_worth", markers=False)
            st.plotly_chart(fignw, use_container_width=True)

            view = base.copy()
            view["date"] = pd.to_datetime(view["date"]).dt.strftime("%Y-%m-%d")
            st.dataframe(view.tail(30), use_container_width=True, hide_index=True)

    # 6) Exportar
    st.divider()
    st.markdown("#### Exportar")
    if df.empty:
        st.info("Nada para exportar.")
    else:
        export_df = df.copy()
        export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV (transações filtradas)",
            data=csv,
            file_name="transacoes_filtradas.csv",
            mime="text/csv"
        )


# =========================================================
# TAB 3: Importar CSV
# =========================================================
with tab3:
    st.subheader("Importação (modelo genérico)")

    st.markdown("""
**Seu CSV deve ter essas colunas (mínimo):**
- `date` (ex: 2026-01-19)
- `description`
- `amount` (positivo entrada, negativo saída)
- `account` (nome da conta)

**Opcional:** `category`, `method`, `notes`
""")

    up = st.file_uploader("Enviar CSV", type=["csv"])
    if up is not None:
        try:
            raw = pd.read_csv(up)
            norm = normalize_import_df(raw)
            st.write("Prévia normalizada:")
            st.dataframe(norm.head(20), use_container_width=True, hide_index=True)

            if st.button("Importar para o banco", type="primary", key="btn_import_csv"):
                for acc in norm["account"].dropna().unique():
                    repo.create_account(acc, "Banco")

                for cat in norm["category"].dropna().unique():
                    repo.create_category(cat, "Despesa")

                # recarrega mapas
                accounts2, categories2, acc_map2, cat_map2, _ = load_accounts_categories()

                for _, row in norm.iterrows():
                    account_id = acc_map2.get(row["account"])
                    category_id = cat_map2.get(row["category"]) if row.get("category") else None
                    repo.insert_transaction(
                        date=row["date"],
                        description=row["description"],
                        amount=float(row["amount"]),
                        account_id=account_id,
                        category_id=category_id,
                        method=row.get("method"),
                        notes=row.get("notes")
                    )

                st.success("Importação concluída. Vá para a aba Dashboard.")
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao ler/importar: {e}")


# =========================================================
# TAB 4: Investimentos (tudo dentro!)
# =========================================================
with tab4:
    st.subheader("Investimentos (Ações/FIIs + Cripto + Renda Fixa)")

    subtabs = st.tabs(["Ativos", "Operações", "Proventos", "Cotações", "Carteira"])

    # dados para investimentos
    accounts_i = repo.list_accounts() or []
    broker_accounts = [r for r in repo.list_accounts() if r["type"] == "Corretora"]
    broker_cash = 0.0
    for a in broker_accounts:
        broker_cash += repo.account_balance_value(int(a["id"]))
    broker_map = {r["name"]: r["id"] for r in broker_accounts}

    assets = invest_repo.list_assets() or []
    asset_label = {r["symbol"]: r["id"] for r in assets} 

    # ===== Ativos =====
    with subtabs[0]:
        st.markdown("### Cadastrar ativo")
        c1, c2, c3, c4 = st.columns([1.2, 2.0, 1.2, 1.2])
        with c1:
            symbol = st.text_input("Ticker/Símbolo", placeholder="PETR4, KNCR11, BTC, CDB_X_2028", key="asset_symbol")
        with c2:
            name = st.text_input("Nome", placeholder="Petrobras PN, Kinea CRI, Bitcoin, CDB Banco X...", key="asset_name")
        with c3:
            asset_class = st.selectbox("Classe", invest_repo.ASSET_CLASSES, key="asset_class")
        with c4:
            currency = st.selectbox("Moeda", ["BRL", "USD"], key="asset_currency")

        c5, c6, c7 = st.columns([1.5, 1.2, 1.3])
        with c5:
            broker = st.selectbox("Conta corretora (opcional)", ["(sem)"] + list(broker_map.keys()), key="asset_broker")
        with c6:
            issuer = st.text_input("Emissor (RF opcional)", placeholder="Banco X", key="asset_issuer")
        with c7:
            maturity_date = st.text_input("Vencimento (RF opcional)", placeholder="YYYY-MM-DD", key="asset_maturity")
       
        # contas que podem ser origem (não-corretora)
        source_accounts = [r for r in accounts if r["type"] != "Corretora"]
        source_map = {r["name"]: r["id"] for r in source_accounts}

        src_name = st.selectbox(
            "Conta origem (opcional) - para transferir automaticamente",
            ["(não transferir)"] + list(source_map.keys()),
            key="trade_src_acc",
        )

        source_account_id = None if src_name == "(não transferir)" else source_map[src_name]

        symbol_preview = symbol.strip().upper().replace(" ", "")
        br_classes = {"Ações BR", "FIIs", "ETFs BR", "BDRs"}
        if symbol_preview and currency == "BRL" and asset_class in br_classes:
            quote_symbol = symbol_preview if symbol_preview.endswith(".SA") else f"{symbol_preview}.SA"
            st.caption(f"Cotação automática (Yahoo) usará: `{quote_symbol}`. Você pode cadastrar sem `.SA`.")

        if st.button("Salvar ativo", type="primary", key="btn_save_asset"):
            if not symbol.strip() or not name.strip():
                st.error("Informe símbolo e nome.")
            else:
                invest_repo.create_asset(
                    symbol=symbol.strip(),
                    name=name.strip(),
                    asset_class=asset_class,
                    source_account_id=source_account_id,
                    currency=currency,
                    broker_account_id=None if broker == "(sem)" else broker_map[broker],
                    issuer=issuer.strip() if issuer.strip() else None,
                    maturity_date=maturity_date.strip() if maturity_date.strip() else None
                )
                st.success("Ativo salvo.")
                st.rerun()

        st.divider()
        st.markdown("### Ativos cadastrados")
        if not assets:
            st.info("Nenhum ativo cadastrado ainda.")
        else:
            df_assets = pd.DataFrame([dict(r) for r in assets])
            assets = invest_repo.list_assets()

        for a in assets:
            if isinstance(a, sqlite3.Row):
                a = dict(a)

            col1, col2, col3, col4 = st.columns([3,3,2,1])

            col1.write(a["symbol"])
            col2.write(a["name"])
            col3.write(a["asset_class"])

            with col4:
                if st.button("Editar", key=f"edit_{a['id']}"):
                    st.session_state["edit_asset_id"] = a["id"]

                if st.button("Excluir", key=f"del_{a['id']}"):
                    ok, msg = invest_repo.delete_asset(a["id"])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
if "edit_asset_id" in st.session_state:
    asset = invest_repo.get_asset_by_id(st.session_state["edit_asset_id"])
    asset = dict(asset)

    st.markdown("### Editar ativo")

    symbol = st.text_input("Symbol", value=asset["symbol"])
    name = st.text_input("Nome", value=asset["name"])
    asset_class = st.text_input("Classe", value=asset["asset_class"])
    currency = st.text_input("Moeda", value=asset["currency"])

    if st.button("Salvar alterações"):
        invest_repo.update_asset(
            asset_id=asset["id"],
            symbol=symbol,
            name=name,
            asset_class=asset_class,
            currency=currency,
            broker_account_id=asset.get("broker_account_id")
        )

        st.success("Ativo atualizado com sucesso.")
        del st.session_state["edit_asset_id"]
        st.rerun()    

# ===== Operações =====
with subtabs[1]:
    st.markdown("### Nova operação (BUY/SELL)")

    if not assets:
        st.warning("Cadastre um ativo primeiro.")
        st.stop()

    c1, c2, c3, c4 = st.columns([1.4, 1.0, 1.0, 1.0])
    with c1:
        sym = st.selectbox("Ativo", list(asset_label.keys()), key="trade_sym")
    with c2:
        trade_date = st.date_input("Data", key="trade_date")
    with c3:
        side = st.selectbox("Tipo", ["BUY", "SELL"], key="trade_side")
    with c4:
        qty = st.number_input("Quantidade", min_value=0.0, step=1.0, format="%.8f", key="trade_qty")

    c5, c6, c7 = st.columns([1.0, 1.0, 2.0])
    with c5:
        price = st.number_input("Preço unitário", min_value=0.0, step=0.01, format="%.8f", key="trade_price")
    with c6:
        fees = st.number_input("Taxas", min_value=0.0, step=0.01, format="%.2f", key="trade_fees")
    with c7:
        note = st.text_input("Obs", placeholder="corretagem, exchange, etc.", key="trade_note")

    # anti-duplo clique
    st.session_state.setdefault("last_trade_key", None)

    if st.button("Salvar operação", type="primary", key="btn_save_trade"):

        # ---------- VALIDACOES ----------
        if float(qty) <= 0 or float(price) <= 0:
            st.error("Quantidade e preço devem ser maiores que zero.")
            st.stop()

        note_norm = note.strip() if note else ""
        gross = float(qty) * float(price)
        total_cost = gross + float(fees)

        asset = dict(invest_repo.get_asset(asset_label[sym]))
        broker_acc_id = asset.get("broker_account_id")
        source_acc_id = asset.get("source_account_id")

        if not broker_acc_id:
            st.error("Ativo sem conta corretora vinculada.")
            st.stop()

        # ---------- SALDO ATUAL ----------
        broker_cash = reports.account_balance_by_id(int(broker_acc_id))

        if side == "BUY" and broker_cash < total_cost:
            st.error(
                f"Saldo insuficiente na corretora.\n\n"
                f"Disponível: {to_brl(broker_cash)}\n"
                f"Necessário: {to_brl(total_cost)}"
            )
            st.stop()

        cat_id = repo.ensure_category("Investimentos", "Transferencia")

        # ---------- MOVIMENTO FINANCEIRO ----------
        if side == "BUY":
            cash = -total_cost
            desc = f"INV BUY {sym}"
        else:
            cash = +(gross - float(fees))
            desc = f"INV SELL {sym}"

        repo.insert_transaction(
            date=trade_date.strftime("%Y-%m-%d"),
            description=desc,
            amount=float(cash),
            account_id=int(broker_acc_id),
            category_id=cat_id,
            method="INV",
            notes=note_norm if note_norm else None
        )

        # ---------- REGISTRA TRADE ----------
        invest_repo.insert_trade(
            asset_id=asset_label[sym],
            date=trade_date.strftime("%Y-%m-%d"),
            side=side,
            quantity=float(qty),
            price=float(price),
            fees=float(fees),
            taxes=0.0,
            note=note_norm if note_norm else None
        )

        st.success("Operação salva.")
        st.rerun()

    st.divider()
    st.markdown("### Operações recentes")
    trades = invest_repo.list_trades()
    if trades:
        recent_trades = [dict(r) for r in trades][:50]

        h1, h2, h3, h4, h5, h6, h7, h8, h9, h10 = st.columns([0.7, 1.1, 1.2, 1.2, 0.9, 1.0, 1.0, 0.8, 0.8, 0.7])
        h1.markdown("**ID**")
        h2.markdown("**Data**")
        h3.markdown("**Ativo**")
        h4.markdown("**Classe**")
        h5.markdown("**Tipo**")
        h6.markdown("**Qtd**")
        h7.markdown("**Preço**")
        h8.markdown("**Taxas**")
        h9.markdown("**Impostos**")
        h10.markdown("**Ação**")

        for t in recent_trades:
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([0.7, 1.1, 1.2, 1.2, 0.9, 1.0, 1.0, 0.8, 0.8, 0.7])
            c1.write(int(t["id"]))
            c2.write(str(t["date"]))
            c3.write(str(t["symbol"]))
            c4.write(str(t["asset_class"]))
            c5.write(str(t["side"]))
            c6.write(f"{float(t['quantity']):.8f}")
            c7.write(f"{float(t['price']):.8f}")
            c8.write(f"{float(t['fees']):.2f}")
            c9.write(f"{float(t['taxes']):.2f}")

            with c10:
                if st.button("Excluir", key=f"btn_del_trade_{int(t['id'])}", help=f"Excluir operação {int(t['id'])}"):
                    ok, msg = invest_repo.delete_trade_with_cash_reversal(int(t["id"]))
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    else:
        st.info("Sem operações ainda.")

    # ===== Proventos =====
    with subtabs[2]:
        st.markdown("### Registrar provento/juros")

        if not assets:
            st.warning("Cadastre um ativo primeiro.")
        else:
            c1, c2, c3, c4 = st.columns([1.5, 1.0, 1.0, 1.5])
            with c1:
                sym_p = st.selectbox("Ativo", list(asset_label.keys()), key="inc_sym")
            with c2:
                date_p = st.date_input("Data", key="inc_date")
            with c3:
                typ = st.selectbox("Tipo", invest_repo.INCOME_TYPES, key="inc_type")
            with c4:
                amount = st.number_input("Valor recebido", min_value=0.0, step=1.0, format="%.2f", key="inc_amount")

            note = st.text_input("Obs (opcional)", key="inc_note")

            st.session_state.setdefault("last_income_key", None)

            if st.button("Salvar provento", type="primary", key="btn_save_income"):
                if float(amount) <= 0:
                    st.error("O valor do provento deve ser maior que zero.")
                    st.stop()

                note_norm = (note.strip() if note else "")
                income_key = (sym_p, date_p.strftime("%Y-%m-%d"), typ, round(float(amount), 2), note_norm)

                if st.session_state["last_income_key"] == income_key:
                    st.warning("Provento já registrado (bloqueio anti-duplicação).")
                    st.stop()

                st.session_state["last_income_key"] = income_key

                invest_repo.insert_income(
                    asset_label[sym_p],
                    date_p.strftime("%Y-%m-%d"),
                    typ,
                    float(amount),
                    note_norm if note_norm else None
                )
                st.success("Provento salvo.")

                asset = invest_repo.get_asset(asset_label[sym_p])
                broker_acc_id = asset["broker_account_id"]
                if broker_acc_id:
                    cat_id = repo.ensure_category("Investimentos", "Receita")
                    desc = f"PROVENTO {sym_p} ({typ})"
                    repo.create_transaction(
                        date=date_p.strftime("%Y-%m-%d"),
                        description=desc,
                        amount=float(amount),
                        category_id=cat_id,
                        account_id=broker_acc_id,
                        method="INV",
                        notes=note_norm if note_norm else None
                    )
                else:
                    st.warning("Ativo sem conta corretora vinculada. Cadastre em Ativos.")

                st.rerun()

        st.divider()
        st.markdown("### Proventos recentes")
        incs = invest_repo.list_income()
        if incs:
            df_inc = pd.DataFrame([dict(r) for r in incs]).head(50)
            st.dataframe(
                df_inc[["id", "date", "symbol", "asset_class", "type", "amount", "note"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Sem proventos ainda.")

   # ===== Cotações =====
    # ===== Cotações =====
        with subtabs[3]:
            st.markdown("### Cotações automáticas")

            if st.button("Atualizar cotação agora", key="btn_update_quotes"):
                try:
                    assets = invest_repo.list_assets()
                    with st.spinner("Consultando cotações (Yahoo/BRAPI)..."):
                        report = invest_quotes.update_all_prices(assets)

                    saved = 0
                    for r in report:
                        if r.get("ok"):
                            invest_repo.upsert_price(
                                asset_id=int(r["asset_id"]),
                                date=str(r["px_date"]),          # YYYY-MM-DD
                                price=float(r["price"]),
                                source=r.get("src") or "brapi",
                            )
                            saved += 1

                    st.success(f"Cotações salvas: {saved}/{len(report)}")
                    if saved < len(report):
                        st.warning("Alguns ativos não retornaram cotação nesta tentativa. Veja a coluna 'error' abaixo.")
                    st.dataframe(pd.DataFrame(report), use_container_width=True)

                except Exception as e:
                    st.error(f"Erro ao atualizar cotação: {e}")

            st.divider()

        st.markdown("### Cadastrar cotação manual")
        if not assets:
            st.warning("Cadastre um ativo primeiro.")
        else:
            c1, c2, c3 = st.columns([1.5, 1.0, 1.0])
            with c1:
                sym = st.selectbox("Ativo", list(asset_label.keys()), key="px_sym")
            with c2:
                px_date = st.date_input("Data", key="px_date")
            with c3:
                price = st.number_input("Cotação / PU / valor unit", min_value=0.0, step=0.01, format="%.8f", key="px_price")

            last = invest_repo.get_last_price_by_symbol(sym)
            if last:
                last = dict(last)  # sqlite Row -> dict
                st.info(
                    f"Última cotação salva: {last['symbol']} = "
                    f"{to_brl(last['price'])} em {last['date']} ({last.get('source','')})"
                )
            else:
                st.warning("Ainda não existe cotação salva para este ativo.")

            src = st.text_input("Fonte (opcional)", placeholder="manual", key="px_src")
            if st.button("Salvar cotação", type="primary", key="btn_save_px"):
                invest_repo.upsert_price(asset_label[sym], px_date.strftime("%Y-%m-%d"), float(price), src.strip() if src.strip() else None)
                st.success("Cotação salva.")
                st.rerun()

    # ===== Carteira =====
    with subtabs[4]:
        st.markdown("### Carteira (visão consolidada)")

        classes = ["(todas)"] + list(invest_repo.ASSET_CLASSES)
        cls_filter = st.selectbox("Filtrar por classe", classes, index=0, key="pf_class_filter")

        pos, tdf, inc = invest_reports.portfolio_view()

        # Sempre calcula saldo corretora (mesmo sem posições)
        # Regra simples: soma saldo de todas as contas do tipo "Corretora"
        all_tx = reports.df_transactions()  # pega tudo (sem filtro de data)
        broker_names = [a["name"] for a in accounts if a["type"] == "Corretora"]

        if all_tx.empty or not broker_names:
            broker_balance = 0.0
        else:
            broker_balance = float(all_tx[all_tx["account"].isin(broker_names)]["amount_brl"].sum())

        # Se quiser usar só a corretora vinculada aos ativos (mais preciso),
        # dá pra refinar depois. Por enquanto isso já resolve o "Saldo Corretora".

        # ===== MODO VAZIO: cria colunas esperadas e totals zerados =====
        is_empty_portfolio = pos.empty

        if is_empty_portfolio:
            # cria um DF vazio com colunas mínimas, pra não quebrar o resto
            pos = pd.DataFrame(columns=[
                "asset_id","symbol","name","asset_class","currency",
                "qty","avg_cost","cost_basis","price","price_date",
                "market_value","unrealized_pnl","realized_pnl","income"
            ])

            total_invested = 0.0
            total_mkt = 0.0
            total_income = 0.0
            total_realized = 0.0
            total_unreal = 0.0
            total_ret = 0.0
            total_ret_pct = 0.0
        else:
            # garante colunas esperadas
            for col in ["income", "realized_pnl", "unrealized_pnl", "market_value", "cost_basis", "price"]:
                if col not in pos.columns:
                    pos[col] = 0.0
            if "price_date" not in pos.columns:
                pos["price_date"] = None
            if "name" not in pos.columns:
                pos["name"] = ""
            if "currency" not in pos.columns:
                pos["currency"] = "BRL"

            # retorno total e %
            pos["total_return"] = (
                pos["unrealized_pnl"].fillna(0.0)
                + pos["realized_pnl"].fillna(0.0)
                + pos["income"].fillna(0.0)
            )
            pos["return_pct"] = pos.apply(
                lambda r: (r["total_return"] / r["cost_basis"] * 100) if float(r["cost_basis"] or 0) > 0 else 0.0,
                axis=1
            )

            total_invested = float(pos["cost_basis"].fillna(0.0).sum())
            total_mkt = float(pos["market_value"].fillna(0.0).sum())
            total_income = float(pos["income"].fillna(0.0).sum())
            total_realized = float(pos["realized_pnl"].fillna(0.0).sum())
            total_unreal = float(pos["unrealized_pnl"].fillna(0.0).sum())
            total_ret = float(pos["total_return"].fillna(0.0).sum())
            total_ret_pct = (total_ret / total_invested * 100) if total_invested > 0 else 0.0

        # ===== KPIs topo (sempre aparecem) =====
        r1c1, r1c2, r1c3 = st.columns(3)
        r1c1.metric("Investido", to_brl(total_invested))
        r1c2.metric("Valor de Mercado", to_brl(total_mkt))
        r1c3.metric("Saldo Corretora", to_brl(broker_balance))

        r2c1, r2c2, r2c3 = st.columns(3)
        r2c1.metric("Proventos", to_brl(total_income))
        r2c2.metric("Retorno Total", to_brl(total_ret), f"{total_ret_pct:.2f}%")
        r2c3.metric("P&L Não Realizado", to_brl(total_unreal))

        st.divider()

        if is_empty_portfolio:
            st.info("Ainda não há posições. Cadastre um ativo e registre uma operação (BUY) para começar.")
            st.caption("Mesmo assim, o Saldo Corretora aparece com base nos lançamentos das contas do tipo Corretora.")
            # aqui você pode parar o resto da renderização da tabela/gráficos:
            st.stop()

        chart_df = pos.copy()
        chart_df["market_value_abs"] = chart_df["market_value"].fillna(0.0)
        chart_df = chart_df[chart_df["market_value_abs"] > 0].sort_values("market_value_abs", ascending=False)

        #left, right = st.columns([1.2, 1.0])
       # with left:
        st.markdown("#### Posições")
        view = pos.copy()
        view["price_date"] = view["price_date"].fillna("").astype(str)

        view["cost_basis_fmt"] = view["cost_basis"].apply(to_brl)
        view["market_value_fmt"] = view["market_value"].apply(to_brl)
        view["unreal_fmt"] = view["unrealized_pnl"].apply(to_brl)
        view["realized_fmt"] = view["realized_pnl"].apply(to_brl)
        view["income_fmt"] = view["income"].apply(to_brl)
        view["total_return_fmt"] = view["total_return"].apply(to_brl)
        view["return_pct_fmt"] = view["return_pct"].apply(lambda x: f"{float(x):.2f}%")

        cols = [
                "symbol", "name", "asset_class",
                "qty", "avg_cost",
                "price_date", "price",
                "cost_basis_fmt", "market_value_fmt",
                "unreal_fmt", "realized_fmt", "income_fmt",
                "total_return_fmt", "return_pct_fmt"
            ]

        rename = {
                "symbol": "Ativo",
                "name": "Nome",
                "asset_class": "Classe",
                "qty": "Qtd",
                "avg_cost": "Preço Médio",
                "price_date": "Data Preço",
                "price": "Preço",
                "cost_basis_fmt": "Investido",
                "market_value_fmt": "Mercado",
                "unreal_fmt": "P&L Não Real.",
                "realized_fmt": "P&L Real.",
                "income_fmt": "Proventos",
                "total_return_fmt": "Retorno Total",
                "return_pct_fmt": "% Retorno",
            }

        table = view[cols].rename(columns=rename).sort_values(["Classe", "Ativo"])
        st.dataframe(table, use_container_width=True, hide_index=True)

        #with right:
        st.markdown("#### Distribuição (Valor de Mercado)")
        if chart_df.empty:
                st.info("Sem valores de mercado (adicione preços).")
        else:
                fig = px.pie(chart_df, names="symbol", values="market_value_abs")
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown("#### Alertas rápidos")
        missing = pos[pos["price"].fillna(0.0) <= 0]
        if not missing.empty:
                st.warning("Alguns ativos estão sem preço. Vá em **Cotações** e registre o preço manual.")
                st.write(", ".join(missing["symbol"].tolist()))
        else:
                st.success("Todos os ativos possuem preço registrado.")

        st.divider()
        st.markdown("#### Totais por classe")
        by_cls = pos.groupby("asset_class", as_index=False).agg(
            invested=("cost_basis", "sum"),
            market=("market_value", "sum"),
            income=("income", "sum"),
            total_return=("total_return", "sum"),
        )
        by_cls["invested"] = by_cls["invested"].apply(to_brl)
        by_cls["market"] = by_cls["market"].apply(to_brl)
        by_cls["income"] = by_cls["income"].apply(to_brl)
        by_cls["total_return"] = by_cls["total_return"].apply(to_brl)

        st.dataframe(
            by_cls.rename(columns={
                "asset_class": "Classe",
                "invested": "Investido",
                "market": "Mercado",
                "income": "Proventos",
                "total_return": "Retorno Total"
            }),
            use_container_width=True,
            hide_index=True
        )
