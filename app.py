# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

import os
from db import init_db, DB_PATH
import repo
import reports
from utils import to_brl, normalize_import_df

import invest_repo
import invest_reports

st.set_page_config(page_title="Financeiro Pessoal", layout="wide")

st.write("📁 CWD:", os.getcwd())
st.write("🗄️ DB_PATH:", DB_PATH)

init_db()

st.title("📊 Controle Financeiro Pessoal (MVP)")

# Sidebar - cadastros
st.sidebar.header("Cadastros")

with st.sidebar.expander("➕ Conta", expanded=False):
    acc_name = st.text_input("Nome da conta", key="acc_name")
    acc_type = st.selectbox("Tipo", ["Banco", "Cartao", "Dinheiro", "Corretora"], key="acc_type")
    if st.button("Salvar conta"):
        if acc_name.strip():
            repo.create_account(acc_name, acc_type)
            st.success("Conta salva.")
        else:
            st.warning("Informe um nome.")

with st.sidebar.expander("➕ Categoria", expanded=False):
    cat_name = st.text_input("Nome da categoria", key="cat_name")
    cat_kind = st.selectbox("Tipo", ["Despesa", "Receita", "Transferencia"], key="cat_kind")
    if st.button("Salvar categoria"):
        if cat_name.strip():
            repo.create_category(cat_name, cat_kind)
            st.success("Categoria salva.")
        else:
            st.warning("Informe um nome.")

accounts = repo.list_accounts()
categories = repo.list_categories()

acc_map = {r["name"]: r["id"] for r in accounts}
cat_map = {r["name"]: r["id"] for r in categories}

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["➕ Lançamentos", "📈 Dashboard", "📥 Importar CSV", "💼 Investimentos"])

# ========== TAB 1: Lançamentos ==========
with tab1:
    st.subheader("Novo lançamento")

    col1, col2, col3, col4 = st.columns([1.2, 2.5, 1.2, 1.2])
    with col1:
        date = st.date_input("Data")
    with col2:
        desc = st.text_input("Descrição")
    with col3:
        amount = st.number_input("Valor (use negativo para despesa)", value=0.0, step=10.0, format="%.2f")
    with col4:
        account_name = st.selectbox("Conta", list(acc_map.keys()) if acc_map else ["(cadastre uma conta)"])

    col5, col6, col7 = st.columns([1.2, 1.2, 2.0])
    with col5:
        category_name = st.selectbox("Categoria (opcional)", ["(sem)"] + list(cat_map.keys()))
    with col6:
        method = st.text_input("Método (opcional)", placeholder="Pix, Débito, Crédito...")
    with col7:
        notes = st.text_input("Obs (opcional)")

    if st.button("Salvar lançamento", type="primary"):
        if not acc_map:
            st.error("Cadastre uma conta antes.")
        elif not desc.strip():
            st.error("Informe a descrição.")
        else:
            account_id = acc_map.get(account_name)
            category_id = None if category_name == "(sem)" else cat_map.get(category_name)
            repo.insert_transaction(
                date=date.strftime("%Y-%m-%d"),
                description=desc,
                amount=float(amount),
                account_id=account_id,
                category_id=category_id,
                method=method if method.strip() else None,
                notes=notes if notes.strip() else None
            )
            st.success("Lançamento salvo.")

    st.divider()
    st.subheader("Lançamentos recentes")

df = reports.df_transactions()
if df.empty:
    st.info("Sem lançamentos ainda.")
else:
    show = df.sort_values("date", ascending=False).head(50).copy()
    show["date"] = show["date"].dt.strftime("%Y-%m-%d")
    show["amount_brl"] = show["amount"].apply(to_brl)
    st.dataframe(
        show[["id", "date", "description", "account", "category", "amount_brl"]],
        use_container_width=True,
        hide_index=True
    )

    col_del, col_btn = st.columns([1.2, 1.0])

    with col_del:
        del_id = st.number_input("Excluir lançamento por ID", min_value=0, step=1, value=0)

    with col_btn:
        if st.button("Excluir"):
            if del_id > 0:
                repo.delete_transaction(int(del_id))
                st.success("Excluído (se existia).")
                st.rerun()
            else:
                st.warning("Informe um ID > 0.")

    st.divider()
    st.markdown("#### Limpeza rápida")

    cA, cB = st.columns([1.2, 2.0])
    with cA:
        if st.button("🧹 Limpar lançamentos INV (teste)"):
            deleted = repo.delete_transactions_by_description_prefix("INV ")
            st.success(f"Removidos {deleted} lançamentos INV.")
            st.rerun()

    with cB:
        st.caption("Remove tudo que começa com 'INV ' (ex: INV BUY..., INV SELL...).")
# ========== TAB 2: Dashboard ==========
with tab2:
    st.subheader("Filtros")

    c1, c2, c3 = st.columns([1.2, 1.2, 2.0])
    with c1:
        date_from = st.date_input("De", value=None)
    with c2:
        date_to = st.date_input("Até", value=None)
    with c3:
        acc_filter = st.selectbox("Conta", ["(todas)"] + list(acc_map.keys()))

    df = reports.df_transactions(
        date_from.strftime("%Y-%m-%d") if date_from else None,
        date_to.strftime("%Y-%m-%d") if date_to else None
    )

    if acc_filter != "(todas)" and not df.empty:
        df = df[df["account"] == acc_filter]

    k = reports.kpis(df)
    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas", to_brl(k["receitas"]))
    k2.metric("Despesas", to_brl(k["despesas"]))  # negativo
    k3.metric("Saldo", to_brl(k["saldo"]))

    st.divider()

    left, right = st.columns([1.2, 1.0])

    with left:
        st.markdown("#### Saldo por mês")
        ms = reports.monthly_summary(df)
        if ms.empty:
            st.info("Sem dados para o período.")
        else:
            fig = px.line(ms, x="month", y="saldo", markers=True)
            st.plotly_chart(fig, use_container_width=True)

            ms_fmt = ms.copy()
            ms_fmt["receitas"] = ms_fmt["receitas"].apply(to_brl)
            ms_fmt["despesas"] = ms_fmt["despesas"].apply(to_brl)
            ms_fmt["saldo"] = ms_fmt["saldo"].apply(to_brl)
            st.dataframe(ms_fmt, use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### Despesas por categoria")
        ce = reports.category_expenses(df)
        if ce.empty:
            st.info("Sem despesas no período.")
        else:
            fig2 = px.bar(ce.head(15), x="valor", y="category", orientation="h")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Saldo por conta")
        ab = reports.account_balance(df)
        if ab.empty:
            st.info("Sem dados.")
        else:
            ab_fmt = ab.copy()
            ab_fmt["saldo"] = ab_fmt["saldo"].apply(to_brl)
            st.dataframe(ab_fmt, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Exportar")
    if df.empty:
        st.info("Nada para exportar.")
    else:
        export_df = df.copy()
        export_df["date"] = export_df["date"].dt.strftime("%Y-%m-%d")
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Baixar CSV (transações filtradas)", data=csv, file_name="transacoes_filtradas.csv", mime="text/csv")

# ========== TAB 3: Importar CSV ==========
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

            if st.button("Importar para o banco", type="primary"):
                # garantir contas/categorias existirem
                for acc in norm["account"].dropna().unique():
                    repo.create_account(acc, "Banco")

                for cat in norm["category"].dropna().unique():
                    # inferir tipo pela sinalização do valor é perigoso; aqui assume Despesa por padrão
                    repo.create_category(cat, "Despesa")

                # recarregar mapas
                accounts2 = repo.list_accounts()
                categories2 = repo.list_categories()
                acc_map2 = {r["name"]: r["id"] for r in accounts2}
                cat_map2 = {r["name"]: r["id"] for r in categories2}

                for _, row in norm.iterrows():
                    account_id = acc_map2.get(row["account"])
                    category_id = cat_map2.get(row["category"]) if row["category"] else None
                    repo.insert_transaction(
                        date=row["date"],
                        description=row["description"],
                        amount=float(row["amount"]),
                        account_id=account_id,
                        category_id=category_id,
                        method=row["method"],
                        notes=row["notes"]
                    )

                st.success("Importação concluída. Vá para a aba Dashboard.")
        except Exception as e:
            st.error(f"Erro ao ler/importar: {e}")



with tab4:
    st.subheader("Investimentos (Ações/FIIs + Cripto + Renda Fixa)")

    subtabs = st.tabs(["Ativos", "Operações", "Proventos", "Cotações", "Carteira"])

    accounts = repo.list_accounts()
    acc_map = {r["name"]: r["id"] for r in accounts}
    broker_accounts = [r for r in accounts if r["type"] == "Corretora"]
    broker_map = {r["name"]: r["id"] for r in broker_accounts}

    assets = invest_repo.list_assets()
    asset_label = {r["symbol"]: r["id"] for r in assets}

    # ===== Ativos =====
    with subtabs[0]:
        st.markdown("### Cadastrar ativo")
        c1, c2, c3, c4 = st.columns([1.2, 2.0, 1.2, 1.2])
        with c1:
            symbol = st.text_input("Ticker/Símbolo", placeholder="PETR4, KNCR11, BTC, CDB_X_2028")
        with c2:
            name = st.text_input("Nome", placeholder="Petrobras PN, Kinea CRI, Bitcoin, CDB Banco X...")
        with c3:
            asset_class = st.selectbox("Classe", invest_repo.ASSET_CLASSES)
        with c4:
            currency = st.selectbox("Moeda", ["BRL", "USD"])

        c5, c6, c7 = st.columns([1.5, 1.2, 1.3])
        with c5:
            broker = st.selectbox("Conta corretora (opcional)", ["(sem)"] + list(broker_map.keys()))
        with c6:
            issuer = st.text_input("Emissor (RF opcional)", placeholder="Banco X")
        with c7:
            maturity_date = st.text_input("Vencimento (RF opcional)", placeholder="YYYY-MM-DD")

        if st.button("Salvar ativo", type="primary"):
            if not symbol.strip() or not name.strip():
                st.error("Informe símbolo e nome.")
            else:
                invest_repo.create_asset(
                    symbol=symbol,
                    name=name,
                    asset_class=asset_class,
                    currency=currency,
                    broker_account_id=None if broker == "(sem)" else broker_map[broker],
                    issuer=issuer if issuer.strip() else None,
                    maturity_date=maturity_date if maturity_date.strip() else None
                )
                st.success("Ativo salvo. Recarregue a página se não aparecer na lista.")

        st.divider()
        st.markdown("### Ativos cadastrados")
        if not assets:
            st.info("Nenhum ativo cadastrado ainda.")
        else:
            df = pd.DataFrame([dict(r) for r in assets])
            st.dataframe(df[["id","symbol","name","asset_class","currency","broker_account"]], use_container_width=True, hide_index=True)

    # ===== Operações =====
with subtabs[1]:
    st.markdown("### Nova operação (BUY/SELL)")

    if not assets:
        st.warning("Cadastre um ativo primeiro.")
    else:
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

        # Anti-duplicação (Streamlit rerun / duplo clique)
        if "last_trade_key" not in st.session_state:
            st.session_state["last_trade_key"] = None

        if st.button("Salvar operação", type="primary", key="btn_save_trade"):

            # Validação
            if float(qty) <= 0 or float(price) <= 0:
                st.error("Quantidade e preço devem ser maiores que zero.")
                st.stop()

            note_norm = (note.strip() if note else "")

            # Chave única da operação (inclui note)
            trade_key = (
                sym,
                side,
                round(float(qty), 8),
                round(float(price), 8),
                round(float(fees), 2),
                trade_date.strftime("%Y-%m-%d"),
                note_norm
            )

            if st.session_state["last_trade_key"] == trade_key:
                st.warning("Operação já registrada (bloqueio anti-duplicação).")
                st.stop()

            st.session_state["last_trade_key"] = trade_key

            # 1) Salvar trade (Investimentos)
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

            # 2) Integração Financeiro ↔ Investimentos (gera lançamento na corretora)
            asset = invest_repo.get_asset(asset_label[sym])
            broker_acc_id = asset["broker_account_id"]

            if broker_acc_id:
                cat_id = repo.ensure_category("Investimentos", "Transferencia")

                gross = float(qty) * float(price)

                if side == "BUY":
                    cash = -(gross + float(fees))
                    desc = f"INV BUY {sym}"
                else:
                    cash = +(gross - float(fees))
                    desc = f"INV SELL {sym}"

                repo.create_transaction(
                    date=trade_date.strftime("%Y-%m-%d"),
                    description=desc,
                    amount=float(cash),
                    category_id=cat_id,
                    account_id=broker_acc_id,
                    method="INV",
                    notes=note_norm if note_norm else None
                )

                st.info(f"Lançamento financeiro criado na corretora (R$ {cash:.2f}).")
            else:
                st.warning(
                    "Ativo sem conta corretora vinculada. "
                    "Vá em Ativos e selecione a conta corretora do ativo."
                )

            st.rerun()

    st.divider()
    st.markdown("### Operações recentes")
    trades = invest_repo.list_trades()
    if trades:
        df = pd.DataFrame([dict(r) for r in trades]).head(50)
        st.dataframe(
            df[["id", "date", "symbol", "asset_class", "side", "quantity", "price", "fees", "taxes", "note"]],
            use_container_width=True,
            hide_index=True
        )
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

        # Anti-duplicação (Streamlit rerun / duplo clique)
        if "last_income_key" not in st.session_state:
            st.session_state["last_income_key"] = None

        if st.button("Salvar provento", type="primary", key="btn_save_income"):

            # Validação
            if float(amount) <= 0:
                st.error("O valor do provento deve ser maior que zero.")
                st.stop()

            note_norm = note.strip() if note else ""

            income_key = (
            sym_p,
            date_p.strftime("%Y-%m-%d"),
            typ,
            round(float(amount), 2),
            (note_norm or "")
        )

            if st.session_state["last_income_key"] == income_key:
                st.warning("Provento já registrado (bloqueio anti-duplicação).")
                st.stop()

            st.session_state["last_income_key"] = income_key

            # 1) Salvar provento (Investimentos) - POSICIONAL (sem keyword 'type')
            invest_repo.insert_income(
                asset_label[sym_p],
                date_p.strftime("%Y-%m-%d"),
                typ,
                float(amount),
                note_norm if note_norm else None
            )
            st.success("Provento salvo.")  

            # 2) Integração Financeiro ↔ Proventos
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
                st.info(f"Receita registrada na corretora (R$ {amount:.2f}).")
            else:
                st.warning(
                    "Ativo sem conta corretora vinculada. "
                    "Vá em Ativos e selecione a conta corretora do ativo."
                )

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
    with subtabs[3]:
        st.markdown("### Cadastrar cotação manual (última cotação do ativo)")
        if not assets:
            st.warning("Cadastre um ativo primeiro.")
        else:
            c1, c2, c3 = st.columns([1.5, 1.0, 1.0])
            with c1:
                sym = st.selectbox("Ativo", list(asset_label.keys()), key="px_sym")
            with c2:
                date = st.date_input("Data", key="px_date")
            with c3:
                price = st.number_input("Cotação / PU / valor unit", min_value=0.0, step=0.01, format="%.8f", key="px_price")

            src = st.text_input("Fonte (opcional)", placeholder="manual")
            if st.button("Salvar cotação", type="primary"):
                invest_repo.upsert_price(asset_label[sym], date.strftime("%Y-%m-%d"), float(price), src if src.strip() else None)
                st.success("Cotação salva.")

    # ===== Carteira =====
    with subtabs[4]:
        st.markdown("### 📌 Carteira (visão consolidada)")

        # filtro opcional por classe
        classes = ["(todas)"] + list(invest_repo.ASSET_CLASSES)
        cls_filter = st.selectbox("Filtrar por classe", classes, index=0)

        # pega visão da carteira
        pos, tdf, inc = invest_reports.portfolio_view()

        if pos.empty:
            st.info("Sem posições ainda. Cadastre um ativo e registre uma operação (BUY) para começar.")
            st.stop()

        # filtro por classe
        if cls_filter != "(todas)":
            pos = pos[pos["asset_class"] == cls_filter].copy()

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
        pos["total_return"] = pos["unrealized_pnl"].fillna(0.0) + pos["realized_pnl"].fillna(0.0) + pos["income"].fillna(0.0)
        pos["return_pct"] = pos.apply(
            lambda r: (r["total_return"] / r["cost_basis"] * 100) if float(r["cost_basis"] or 0) > 0 else 0.0,
            axis=1
        )

        # KPIs topo
        total_invested = float(pos["cost_basis"].fillna(0.0).sum())
        total_mkt = float(pos["market_value"].fillna(0.0).sum())
        total_income = float(pos["income"].fillna(0.0).sum())
        total_realized = float(pos["realized_pnl"].fillna(0.0).sum())
        total_unreal = float(pos["unrealized_pnl"].fillna(0.0).sum())
        total_ret = float(pos["total_return"].fillna(0.0).sum())
        total_ret_pct = (total_ret / total_invested * 100) if total_invested > 0 else 0.0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Investido", to_brl(total_invested))
        k2.metric("Valor de Mercado", to_brl(total_mkt))
        k3.metric("Proventos", to_brl(total_income))
        k4.metric("Retorno Total", to_brl(total_ret), f"{total_ret_pct:.2f}%")
        k5.metric("P&L Não Realizado", to_brl(total_unreal))

        st.divider()

        # gráfico: distribuição por valor de mercado
        chart_df = pos.copy()
        chart_df["market_value_abs"] = chart_df["market_value"].fillna(0.0)
        chart_df = chart_df[chart_df["market_value_abs"] > 0].sort_values("market_value_abs", ascending=False)

        left, right = st.columns([1.2, 1.0])

        with left:
            st.markdown("#### 🧾 Posições")
            view = pos.copy()

            # formata datas e valores
            if "price_date" in view.columns:
                view["price_date"] = view["price_date"].fillna("").astype(str)

            view["qty"] = view["qty"].astype(float)
            view["avg_cost"] = view["avg_cost"].astype(float)
            view["cost_basis_fmt"] = view["cost_basis"].apply(to_brl)
            view["price_fmt"] = view["price"].apply(lambda x: to_brl(float(x)) if str(view["currency"].iloc[0]) == "BRL" else f"{float(x):.4f}")
            view["market_value_fmt"] = view["market_value"].apply(to_brl)
            view["unreal_fmt"] = view["unrealized_pnl"].apply(to_brl)
            view["realized_fmt"] = view["realized_pnl"].apply(to_brl)
            view["income_fmt"] = view["income"].apply(to_brl)
            view["total_return_fmt"] = view["total_return"].apply(to_brl)
            view["return_pct_fmt"] = view["return_pct"].apply(lambda x: f"{float(x):.2f}%")

            cols = [
                "symbol", "name", "asset_class",
                "qty", "avg_cost",
                "price_date", "price_fmt",
                "cost_basis_fmt", "market_value_fmt",
                "unreal_fmt", "realized_fmt", "income_fmt",
                "total_return_fmt", "return_pct_fmt"
            ]

            # renomeia cabeçalhos
            rename = {
                "symbol": "Ativo",
                "name": "Nome",
                "asset_class": "Classe",
                "qty": "Qtd",
                "avg_cost": "Preço Médio",
                "price_date": "Data Preço",
                "price_fmt": "Preço",
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

        with right:
            st.markdown("#### 🥧 Distribuição (Valor de Mercado)")
            if chart_df.empty:
                st.info("Sem valores de mercado (adicione preços).")
            else:
                fig = px.pie(chart_df, names="symbol", values="market_value_abs")
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.markdown("#### 🔎 Alertas rápidos")
            # preço faltando
            missing = pos[pos["price"].fillna(0.0) <= 0]
            if not missing.empty:
                st.warning("Alguns ativos estão sem preço. Vá em **Cotações** e registre o preço manual por enquanto.")
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

        st.dataframe(by_cls.rename(columns={
            "asset_class": "Classe",
            "invested": "Investido",
            "market": "Mercado",
            "income": "Proventos",
            "total_return": "Retorno Total"
        }), use_container_width=True, hide_index=True)