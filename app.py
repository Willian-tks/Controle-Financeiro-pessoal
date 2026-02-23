# app.py

import os
import time
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
from nav_component import sidebar_nav
import auth
from tenant import set_current_user_id, clear_current_user_id

import invest_repo
import invest_reports
import invest_quotes

st.set_page_config(page_title="Financeiro Pessoal", layout="wide")
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#3b82f6", "#34d399", "#f59e0b", "#fb7185", "#22c55e", "#a78bfa"]


def _extract_invite_token(raw: str) -> str:
    v = (raw or "").strip()
    if not v:
        return ""

    # URL completa
    if "invite=" in v:
        v = v.split("invite=", 1)[1]

    # valor colado como query parcial
    if v.startswith("?"):
        v = v[1:]
    if v.startswith("invite="):
        v = v.split("=", 1)[1]

    # remove resto de query/hash
    for sep in ("&", "#"):
        if sep in v:
            v = v.split(sep, 1)[0]

    return v.strip()


def normalize_assets_import_df(df: pd.DataFrame) -> pd.DataFrame:
    alias = {
        "ticker/símbolo": "symbol",
        "ticker/simbolo": "symbol",
        "ticker": "symbol",
        "símbolo": "symbol",
        "simbolo": "symbol",
        "nome": "name",
        "classe": "asset_class",
        "setor": "sector",
        "sector": "sector",
        "moeda": "currency",
        "conta corretora (opcional)": "broker_account",
        "conta corretora": "broker_account",
        "conta origem (opcional)": "source_account",
        "conta origem": "source_account",
    }
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    mapped_cols = []
    for c in df.columns:
        key = c.lower().strip()
        mapped_cols.append(alias.get(key, key))
    df.columns = mapped_cols

    required = {"symbol", "name", "asset_class"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV de ativos faltando colunas obrigatórias: {sorted(list(missing))}")

    if "currency" not in df.columns:
        df["currency"] = "BRL"
    if "sector" not in df.columns:
        df["sector"] = "Não definido"
    if "broker_account" not in df.columns:
        df["broker_account"] = None
    if "source_account" not in df.columns:
        df["source_account"] = None

    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["name"] = df["name"].astype(str).str.strip()
    df["asset_class"] = df["asset_class"].astype(str).str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()
    df["currency"] = df["currency"].astype(str).str.strip().str.upper().replace({"": "BRL"})
    df["broker_account"] = df["broker_account"].astype(str).str.strip()
    df["source_account"] = df["source_account"].astype(str).str.strip()

    class_map = {
        "ACOES BR": "Ações BR",
        "AÇÕES BR": "Ações BR",
        "ACOES": "Ações BR",
        "AÇÕES": "Ações BR",
        "FIIS": "FIIs",
        "FIIS ": "FIIs",
        "FILS": "FIIs",
        "FIIS BR": "FIIs",
        "BDRS": "BDRs",
        "ETFS BR": "ETFs BR",
    }
    df["asset_class"] = df["asset_class"].apply(
        lambda x: class_map.get(str(x).upper().strip(), str(x).strip())
    )
    sector_map = {
        "FINANCEIRO": "Financeiro",
        "ENERGIA E UTILIDADES": "Energia & Utilidades",
        "ENERGIA & UTILIDADES": "Energia & Utilidades",
        "COMMODITIES": "Commodities",
        "CONSUMO": "Consumo",
        "INDUSTRIA": "Indústria",
        "INDÚSTRIA": "Indústria",
        "SERVICOS": "Serviços",
        "SERVIÇOS": "Serviços",
        "TECNOLOGIA E TELECOM": "Tecnologia & Telecom",
        "TECNOLOGIA & TELECOM": "Tecnologia & Telecom",
        "IMOBILIARIO": "Imobiliário",
        "IMOBILIÁRIO": "Imobiliário",
        "NAO DEFINIDO": "Não definido",
        "NÃO DEFINIDO": "Não definido",
        "": "Não definido",
    }
    df["sector"] = df["sector"].apply(
        lambda x: sector_map.get(str(x).upper().strip(), str(x).strip() or "Não definido")
    )
    valid_sectors = set(invest_repo.ASSET_SECTORS)
    df["sector"] = df["sector"].apply(lambda s: s if s in valid_sectors else "Não definido")

    df = df[(df["symbol"] != "") & (df["name"] != "")]
    return df


def _parse_brl_decimal(raw: str) -> float:
    s = (raw or "").strip().replace("R$", "").replace(" ", "")
    if not s:
        raise ValueError("vazio")

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")

    return float(s)


def _parse_qty_input(raw: str, allow_fraction: bool) -> float:
    s = (raw or "").strip().replace(" ", "")
    if not s:
        raise ValueError("vazio")

    if allow_fraction:
        if s.count(",") + s.count(".") > 1:
            raise ValueError("Quantidade inválida.")
        s = s.replace(",", ".")
        val = float(s)
    else:
        if not s.isdigit():
            raise ValueError("Quantidade deve ser número inteiro (sem vírgula/ponto).")
        val = float(int(s))

    return val


def _mask_trade_price_input() -> None:
    raw = str(st.session_state.get("trade_price_txt", "") or "").strip()
    if not raw:
        st.session_state["trade_price_txt"] = ""
        return

    try:
        val = _parse_brl_decimal(raw)
    except Exception:
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            st.session_state["trade_price_txt"] = ""
            return
        val = int(digits) / 100.0

    st.session_state["trade_price_txt"] = to_brl(float(val)).replace("R$ ", "")


def _mask_currency_input_key(key: str) -> None:
    raw = str(st.session_state.get(key, "") or "").strip()
    if not raw:
        st.session_state[key] = ""
        return
    try:
        val = _parse_brl_decimal(raw)
    except Exception:
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            st.session_state[key] = ""
            return
        val = int(digits) / 100.0
    st.session_state[key] = to_brl(float(val)).replace("R$ ", "")


def _mask_integer_input_key(key: str) -> None:
    raw = str(st.session_state.get(key, "") or "")
    digits = "".join(ch for ch in raw if ch.isdigit())
    st.session_state[key] = digits


def inject_corporate_css():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

      :root {
        --bg-page: #dfe2ea;
        --bg-shell: #eef1f7;
        --bg-surface: #ffffff;
        --text-main: #132238;
        --text-muted: #677185;
        --line: #d7dce8;
        --primary: #2b95f9;
        --sidebar-a: #132a56;
        --sidebar-b: #1a3f76;
      }

      html, body, [class*="css"] {
        font-family: "Manrope", "Segoe UI", sans-serif;
      }

      .stApp {
        background: var(--bg-page);
      }
      .main .block-container {
        max-width: 1260px;
        margin-top: 1rem;
        margin-bottom: 1.6rem;
        padding: 1.2rem 1.3rem 1.6rem 1.3rem;
        background: var(--bg-shell);
        border: 1px solid #cfd5e3;
        border-radius: 20px;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
      }
      hr { margin: 1.2rem 0; border-color: #d6dbe7; }

      section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-a) 0%, var(--sidebar-b) 100%);
        border-right: 0;
      }
      section[data-testid="stSidebar"] * {
        color: #eaf1ff !important;
      }
      section[data-testid="stSidebar"] .stTextInput input,
      section[data-testid="stSidebar"] .stNumberInput input,
      section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.10) !important;
        border-color: rgba(255,255,255,0.22) !important;
      }
      section[data-testid="stSidebar"] div.stButton > button {
        background: #f3f6fc !important;
        color: #17315d !important;
        border: 1px solid #d3ddef !important;
      }
      section[data-testid="stSidebar"] div.stButton > button * {
        color: #17315d !important;
      }
      section[data-testid="stSidebar"] div.stButton > button:hover {
        background: #e7eefb !important;
        color: #10284e !important;
      }
      section[data-testid="stSidebar"] div.stButton > button:hover * {
        color: #10284e !important;
      }
      section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: #fee2e2 !important;
        color: #991b1b !important;
        border: 1px solid #fecaca !important;
      }
      section[data-testid="stSidebar"] div.stButton > button[kind="primary"] * {
        color: #991b1b !important;
      }
      section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
        background: #fecaca !important;
        color: #7f1d1d !important;
      }
      section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover * {
        color: #7f1d1d !important;
      }
      section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.18);
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        margin: 0 !important;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.15rem !important;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {
        min-height: 3.2rem;
        border-radius: 12px;
        padding: 0.45rem 0.65rem;
        border: 1px solid transparent;
        background: rgba(255,255,255,0.02);
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label p {
        color: #9db2d7 !important;
        font-weight: 700 !important;
        font-size: 0.96rem !important;
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(255,255,255,0.14);
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: rgba(48, 124, 255, 0.22);
        border-color: rgba(96, 165, 250, 0.7);
      }
      section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) p {
        color: #ecf5ff !important;
      }
      .sb-logo {
        width: 64px;
        height: 64px;
        margin: 2px auto 12px auto;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 34px;
        font-weight: 800;
        color: #32b2ff !important;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.15);
      }
      section[data-testid="stSidebar"] iframe[title="sidebar_nav"] {
        background: transparent !important;
        border: 0 !important;
      }

      h1, h2, h3 {
        letter-spacing: -0.02em;
        color: var(--text-main);
      }
      h1 { font-weight: 800; }
      h2, h3 { font-weight: 700; }
      p, li, label, div {
        color: var(--text-main);
      }
      [data-testid="stCaptionContainer"] p {
        color: var(--text-muted);
      }

      /* Cards / métricas */
      .card {
        background: var(--bg-surface);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(15,23,42,0.05);
        margin-bottom: 14px;
      }
      .card-title {
        font-weight: 800;
        margin: 0 0 8px 0;
      }
      .muted { color: var(--text-muted); }

      [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 10px 12px;
        box-shadow: 0 6px 18px rgba(15,23,42,0.04);
      }
      [data-testid="stMetricLabel"] {
        color: #445169;
        font-weight: 700;
      }
      [data-testid="stMetricValue"] {
        color: #18263c;
        font-weight: 800;
      }
      [data-testid="stMetricDelta"] {
        font-weight: 700;
      }

      /* Badges */
      .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 650;
        border: 1px solid var(--line);
        background: #f7f9fc;
        color: #132238;
      }
      .badge-ok { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
      .badge-warn { background: #fffbeb; border-color: #fde68a; color: #92400e; }
      .badge-bad { background: #fef2f2; border-color: #fecaca; color: #991b1b; }

      /* Botões */
      div.stButton > button {
        border-radius: 11px !important;
        padding: 0.55rem 1rem !important;
        font-weight: 700 !important;
        border: 1px solid #cfd7e7 !important;
        background: #ffffff !important;
      }
      div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%) !important;
        color: #ffffff !important;
        border-color: #0ea5e9 !important;
      }

      /* Inputs */
      div[data-baseweb="input"] input, textarea {
        border-radius: 12px !important;
        border: 1px solid #d5dbea !important;
        background: #ffffff !important;
      }
      div[data-baseweb="select"] > div {
        border-radius: 12px !important;
        border: 1px solid #d5dbea !important;
        background: #ffffff !important;
      }

      /* Tabs com visual de navegação */
      [data-testid="stTabs"] [role="tablist"] {
        gap: 10px;
        border-bottom: 0;
        background: #e8ecf5;
        padding: 8px;
        border-radius: 12px;
      }
      [data-testid="stTabs"] [role="tab"] {
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 700;
        color: #40506b;
      }
      [data-testid="stTabs"] [aria-selected="true"] {
        background: #ffffff;
        color: #12233a;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.08);
      }

      /* DataFrame */
      div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #d5dbea;
        background: #ffffff;
      }

      /* Alertas (deixa mais corporativo) */
      div[data-testid="stAlert"] {
        border-radius: 14px;
        border: 1px solid #d6dbe8;
      }

      /* Plotly */
      [data-testid="stPlotlyChart"] > div {
        border-radius: 14px;
        border: 1px solid #d5dbea;
        background: #ffffff;
        padding: 6px;
      }
    </style>
    """, unsafe_allow_html=True)

inject_corporate_css()


# ----------------------------
# Config
# ----------------------------
st.title("Controle Financeiro Pessoal (MVP)")
st.caption("Painel financeiro pessoal")

init_db()
auth.ensure_bootstrap_admin()


def render_auth_gate():
    st.subheader("Entrar")
    invite_token_qp = str(st.query_params.get("invite", "")).strip()
    login_tab, invite_tab = st.tabs(["Login", "Cadastro por convite"])

    with login_tab:
        email = st.text_input("E-mail", key="login_email")
        password = st.text_input("Senha", type="password", key="login_password")
        if st.button("Entrar", type="primary", key="btn_login"):
            user = auth.authenticate_user(email, password)
            if not user:
                st.error("Credenciais inválidas.")
            else:
                auth.login_session(user["id"])
                auth.claim_legacy_data_for_user(user["id"])
                st.rerun()

    with invite_tab:
        st.caption("Para criar usuário, use um link de convite gerado pelo admin.")
        token = st.text_input("Token do convite", value=invite_token_qp, key="invite_token")
        token_norm = _extract_invite_token(token)
        if token and token != token_norm:
            st.caption("Token extraído automaticamente do link.")

        if token_norm:
            ok, msg, _inv = auth.validate_invite(token_norm)
            if ok:
                st.success(msg)
            else:
                st.warning(msg)

        name = st.text_input("Nome", key="signup_name")
        email = st.text_input("E-mail", key="signup_email")
        password = st.text_input("Senha", type="password", key="signup_password")
        confirm = st.text_input("Confirmar senha", type="password", key="signup_password2")

        if st.button("Criar conta com convite", type="primary", key="btn_signup"):
            if password != confirm:
                st.error("As senhas não conferem.")
            else:
                ok, msg, user = auth.register_user_with_invite(token_norm, email, password, name)
                if not ok:
                    st.error(msg)
                else:
                    st.query_params.clear()
                    auth.login_session(user["id"])
                    auth.claim_legacy_data_for_user(user["id"])
                    st.success(msg)
                    st.rerun()


current_user = auth.session_user()
if not current_user:
    render_auth_gate()
    st.stop()

set_current_user_id(int(current_user["id"]))

if current_user.get("role") == "admin":
    st.sidebar.divider()
    st.sidebar.subheader("Convites")
    invited_email = st.sidebar.text_input("E-mail convidado (opcional)", key="invite_email")
    invite_days = st.sidebar.number_input("Expira em (dias)", min_value=1, max_value=60, value=7, step=1, key="invite_days")
    if st.sidebar.button("Gerar convite", key="btn_create_invite"):
        ok, msg, inv = auth.create_invite(
            admin_user_id=int(current_user["id"]),
            invited_email=invited_email.strip() if invited_email.strip() else None,
            expires_days=int(invite_days),
        )
        if ok:
            base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
            invite_link = f"{base_url}?invite={inv['token']}" if base_url else f"?invite={inv['token']}"
            st.sidebar.success("Convite gerado.")
            st.sidebar.code(invite_link, language="text")
        else:
            st.sidebar.error(msg)

    with st.sidebar.expander("Convites recentes", expanded=False):
        invites = auth.list_recent_invites(int(current_user["id"]), limit=10)
        if not invites:
            st.write("Sem convites.")
        else:
            for inv in invites:
                used = "usado" if inv.get("used_at") else "pendente"
                st.write(
                    f"{inv['id']} | {inv.get('invited_email') or '(qualquer e-mail)'} | "
                    f"expira: {inv['expires_at']} | {used}"
                )

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
# Sidebar - Navegação
# =========================================================
with st.sidebar:
    st.divider()
    page_icons = {
        "Gerenciador": "settings",
        "Contas": "wallet",
        "Lançamentos": "receipt",
        "Dashboard": "chart",
        "Importar CSV": "import",
        "Investimentos": "coins",
    }
    page_options = list(page_icons.keys())
    selected_page = sidebar_nav(
        options=page_options,
        icons=page_icons,
        selected=st.session_state.get("main_page_nav", "Gerenciador"),
        key="main_sidebar_component",
    )
    st.session_state["main_page_nav"] = selected_page

    st.divider()
    st.caption(f"Usuário: {current_user.get('display_name') or current_user['email']}")
    st.caption(f"Perfil: {current_user.get('role', 'user')}")
    if st.button("Sair", key="btn_logout", type="primary"):
        auth.logout_session()
        clear_current_user_id()
        st.rerun()


# =========================================================
# Página: Gerenciador
# =========================================================
if selected_page == "Gerenciador":
    st.subheader("Gerenciador")
    cad_tab1, cad_tab2, cad_tab3 = st.tabs(["Contas", "Categorias", "Limpeza"])

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

    with cad_tab3:
        st.markdown("### Limpeza de dados (TESTES)")
        st.caption(
            "Use apenas em ambiente de testes.\n"
            "Digite LIMPAR para habilitar os botões."
        )

        confirm = st.text_input(
            "Confirmação",
            placeholder="Digite LIMPAR",
            key="confirm_clear"
        )

        c1, c2 = st.columns(2)
        c3, c4 = st.columns(2)

        with c1:
            if st.button("Lançamentos", disabled=(confirm != "LIMPAR")):
                n = repo.clear_transactions()
                st.success(f"{n} lançamentos removidos")
                st.rerun()

        with c2:
            if st.button("Mov. Invest.", disabled=(confirm != "LIMPAR")):
                res = invest_repo.clear_invest_movements()
                st.success(
                    f"Trades: {res['trades']} | "
                    f"Proventos: {res['income_events']} | "
                    f"Cotações: {res['prices']}"
                )
                st.rerun()

        with c3:
            if st.button("Ativos", disabled=(confirm != "LIMPAR")):
                try:
                    n = invest_repo.clear_assets()
                    st.success(f"{n} ativos removidos")
                    st.rerun()
                except Exception:
                    st.error(
                        "Erro ao remover ativos.\n"
                        "Limpe primeiro trades, proventos e cotações."
                    )

        with c4:
            if st.button("RESET TOTAL", disabled=(confirm != "LIMPAR")):
                repo.clear_transactions()
                invest_repo.clear_invest_movements()
                invest_repo.clear_assets()
                st.success("Base de investimentos zerada.")
                st.rerun()

# Recarrega mapas (pois gerenciador pode ter alterado)
accounts, categories, acc_map, acc_type_map, cat_map, cat_kind_map = load_accounts_categories()


# =========================================================
# Páginas principais
# =========================================================
# ========== TAB 0: Contas (Saldos) ==========
if selected_page == "Contas":
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
if selected_page == "Lançamentos":
    st.subheader("Novo lançamento")

    col1, col2, col3, col4 = st.columns([1.2, 2.5, 1.2, 1.2])
    with col1:
        date = st.date_input("Data", key="tx_date", format="DD/MM/YYYY")
    with col2:
        desc = st.text_input("Descrição", key="tx_desc")
    with col3:
        amount_abs_txt = st.text_input(
            "Valor",
            value=st.session_state.get("tx_amount_txt", ""),
            placeholder="0,00",
            key="tx_amount_txt",
            on_change=lambda: _mask_currency_input_key("tx_amount_txt"),
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
        try:
            amount = _parse_brl_decimal(amount_abs_txt)
        except Exception:
            st.error("Valor inválido. Exemplo válido: 1.234,56")
            st.stop()

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
            del_id_txt = st.text_input(
                "Excluir lançamento por ID",
                value=st.session_state.get("tx_del_id_txt", ""),
                placeholder="Ex: 123",
                key="tx_del_id_txt",
                on_change=lambda: _mask_integer_input_key("tx_del_id_txt"),
            )
        with col_btn:
            if st.button("Excluir", key="btn_del_tx"):
                if str(del_id_txt).strip().isdigit() and int(del_id_txt) > 0:
                    repo.delete_transaction(int(del_id_txt))
                    st.success("Excluído (se existia).")
                    st.rerun()
                else:
                    st.warning("Informe um ID > 0.")


# =========================================================
# TAB 2: Dashboard (tudo aqui dentro!)
# =========================================================
if selected_page == "Dashboard":
    st.subheader("Filtros")

    f1, f2, f3 = st.columns([1.2, 1.2, 2.0])
    with f1:
        date_from = st.date_input("De", value=None, key="dash_date_from", format="DD/MM/YYYY")
    with f2:
        date_to = st.date_input("Até", value=None, key="dash_date_to", format="DD/MM/YYYY")
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
if selected_page == "Importar CSV":
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
                accounts2, categories2, acc_map2, _acc_type_map2, cat_map2, _cat_kind_map2 = load_accounts_categories()

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
if selected_page == "Investimentos":
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
    asset_dicts = [dict(r) for r in assets]
    asset_label = {r["symbol"]: r["id"] for r in asset_dicts}
    asset_meta = {r["symbol"]: r for r in asset_dicts}

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
        sector = st.selectbox("Setor", invest_repo.ASSET_SECTORS, key="asset_sector")

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
                created = invest_repo.create_asset(
                    symbol=symbol.strip(),
                    name=name.strip(),
                    asset_class=asset_class,
                    sector=sector,
                    source_account_id=source_account_id,
                    currency=currency,
                    broker_account_id=None if broker == "(sem)" else broker_map[broker],
                    issuer=issuer.strip() if issuer.strip() else None,
                    maturity_date=maturity_date.strip() if maturity_date.strip() else None
                )
                if created:
                    st.success("Ativo salvo.")
                else:
                    st.warning("Ativo já existia para este usuário.")
                st.rerun()

        st.divider()
        st.markdown("### Importar ativos por CSV")
        st.caption("Aceita CSV com separador `,` ou `;`.")
        up_assets = st.file_uploader("Enviar CSV de ativos", type=["csv"], key="asset_csv_upload")
        if up_assets is not None:
            try:
                raw_assets = pd.read_csv(up_assets, sep=None, engine="python")
                norm_assets = normalize_assets_import_df(raw_assets)
                st.write("Prévia normalizada:")
                st.dataframe(norm_assets.head(30), use_container_width=True, hide_index=True)

                if st.button("Importar ativos", type="primary", key="btn_import_assets_csv"):
                    # Recarrega contas atuais para mapear corretora/origem por nome.
                    acc_rows = repo.list_accounts() or []
                    acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
                    acc_name_to_type = {r["name"]: r["type"] for r in acc_rows}

                    inserted = 0
                    skipped = 0
                    errors = []

                    for _, row in norm_assets.iterrows():
                        sym = str(row["symbol"]).strip().upper()
                        nm = str(row["name"]).strip()
                        cls = str(row["asset_class"]).strip()
                        sector = str(row.get("sector", "Não definido")).strip() or "Não definido"
                        cur = str(row.get("currency", "BRL")).strip().upper() or "BRL"
                        broker_name = str(row.get("broker_account", "")).strip()
                        source_name = str(row.get("source_account", "")).strip()

                        if not sym or not nm or not cls:
                            skipped += 1
                            continue

                        broker_id = None
                        if broker_name:
                            if broker_name not in acc_name_to_id:
                                repo.create_account(broker_name, "Corretora")
                                acc_rows = repo.list_accounts() or []
                                acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
                                acc_name_to_type = {r["name"]: r["type"] for r in acc_rows}
                            if acc_name_to_type.get(broker_name) != "Corretora":
                                errors.append(f"{sym}: conta '{broker_name}' existe mas não é do tipo Corretora.")
                                skipped += 1
                                continue
                            broker_id = acc_name_to_id.get(broker_name)

                        source_id = None
                        if source_name:
                            if source_name not in acc_name_to_id:
                                repo.create_account(source_name, "Banco")
                                acc_rows = repo.list_accounts() or []
                                acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
                            source_id = acc_name_to_id.get(source_name)

                        try:
                            created = invest_repo.create_asset(
                                symbol=sym,
                                name=nm,
                                asset_class=cls,
                                sector=sector,
                                currency=cur,
                                broker_account_id=broker_id,
                                source_account_id=source_id,
                            )
                            if created:
                                inserted += 1
                            else:
                                skipped += 1
                        except Exception as e:
                            errors.append(f"{sym}: {e}")
                            skipped += 1

                    if inserted > 0:
                        st.success(f"Importação concluída. Ativos processados: {inserted}.")
                    if skipped > 0:
                        st.warning(f"Linhas ignoradas/com erro: {skipped}.")
                    if errors:
                        st.write("Detalhes:")
                        st.dataframe(pd.DataFrame({"erro": errors[:50]}), use_container_width=True, hide_index=True)
                    st.rerun()

            except Exception as e:
                st.error(f"Erro ao ler/importar CSV de ativos: {e}")

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

            col1, col2, col3, col4, col5 = st.columns([2.5, 3, 2, 2, 1])

            col1.write(a["symbol"])
            col2.write(a["name"])
            col3.write(a["asset_class"])
            col4.write(a.get("sector") or "Não definido")

            with col5:
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
            asset_class = st.selectbox(
                "Classe",
                invest_repo.ASSET_CLASSES,
                index=list(invest_repo.ASSET_CLASSES).index(asset["asset_class"]) if asset["asset_class"] in invest_repo.ASSET_CLASSES else 0,
            )
            sector_val = asset.get("sector") or "Não definido"
            sector = st.selectbox(
                "Setor",
                invest_repo.ASSET_SECTORS,
                index=invest_repo.ASSET_SECTORS.index(sector_val) if sector_val in invest_repo.ASSET_SECTORS else 0,
            )
            currency = st.selectbox("Moeda", ["BRL", "USD"], index=0 if str(asset["currency"]).upper() == "BRL" else 1)

            if st.button("Salvar alterações"):
                invest_repo.update_asset(
                    asset_id=asset["id"],
                    symbol=symbol,
                    name=name,
                    asset_class=asset_class,
                    sector=sector,
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

    if st.session_state.get("reset_trade_form", False):
        st.session_state["trade_qty_txt"] = ""
        st.session_state["trade_price_txt"] = ""
        st.session_state["trade_fees_txt"] = ""
        st.session_state["trade_note"] = ""
        st.session_state["reset_trade_form"] = False

    c1, c2, c3, c4 = st.columns([1.4, 1.0, 1.0, 1.0])
    with c1:
        sym = st.selectbox("Ativo", list(asset_label.keys()), key="trade_sym")
    with c2:
        trade_date = st.date_input("Data", key="trade_date", format="DD/MM/YYYY")
    with c3:
        side = st.selectbox("Tipo", ["BUY", "SELL"], key="trade_side")
    selected_asset = asset_meta.get(sym, {})
    selected_asset_class = str(selected_asset.get("asset_class", ""))
    allow_fraction_qty = ("STOCK" in selected_asset_class.upper()) or (selected_asset_class.strip().upper() == "CRYPTO")
    with c4:
        qty_txt = st.text_input(
            "Quantidade",
            value=st.session_state.get("trade_qty_txt", ""),
            placeholder="Ex: 10,5" if allow_fraction_qty else "Ex: 220",
            key="trade_qty_txt",
        )

    c5, c6, c7 = st.columns([1.0, 1.0, 2.0])
    with c5:
        price_txt = st.text_input(
            "Preço unitário",
            value=st.session_state.get("trade_price_txt", ""),
            placeholder="0,00",
            key="trade_price_txt",
            on_change=_mask_trade_price_input,
        )
        try:
            _price_preview = _parse_brl_decimal(price_txt) if price_txt.strip() else None
            if _price_preview is not None:
                st.caption(f"Preço formatado: {to_brl(_price_preview)}")
        except Exception:
            st.caption("Preço inválido. Use apenas números, vírgula e ponto.")
    with c6:
        fees_txt = st.text_input(
            "Taxas",
            value=st.session_state.get("trade_fees_txt", ""),
            placeholder="0,00",
            key="trade_fees_txt",
            on_change=lambda: _mask_currency_input_key("trade_fees_txt"),
        )
    with c7:
        note = st.text_input("Obs", placeholder="corretagem, exchange, etc.", key="trade_note")

    # anti-duplo clique
    st.session_state.setdefault("last_trade_key", None)

    if st.button("Salvar operação", type="primary", key="btn_save_trade"):

        # ---------- VALIDACOES ----------
        try:
            qty = _parse_qty_input(qty_txt, allow_fraction=allow_fraction_qty)
        except Exception:
            if allow_fraction_qty:
                st.error("Quantidade inválida. Para este ativo, use número (ex.: 10,5).")
            else:
                st.error("Quantidade deve ser inteira, sem vírgula ou ponto.")
            st.stop()

        try:
            price = _parse_brl_decimal(price_txt)
        except Exception:
            st.error("Preço unitário inválido. Exemplo válido: 18,83")
            st.stop()

        try:
            fees = _parse_brl_decimal(fees_txt) if fees_txt.strip() else 0.0
        except Exception:
            st.error("Taxas inválidas. Exemplo válido: 1,99")
            st.stop()

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

        st.session_state["reset_trade_form"] = True
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
            if st.session_state.get("reset_income_form", False):
                st.session_state["inc_amount_txt"] = ""
                st.session_state["reset_income_form"] = False

            c1, c2, c3, c4 = st.columns([1.5, 1.0, 1.0, 1.5])
            with c1:
                sym_p = st.selectbox("Ativo", list(asset_label.keys()), key="inc_sym")
            with c2:
                date_p = st.date_input("Data", key="inc_date", format="DD/MM/YYYY")
            with c3:
                typ = st.selectbox("Tipo", invest_repo.INCOME_TYPES, key="inc_type")
            with c4:
                amount_txt = st.text_input(
                    "Valor recebido",
                    value=st.session_state.get("inc_amount_txt", ""),
                    placeholder="0,00",
                    key="inc_amount_txt",
                    on_change=lambda: _mask_currency_input_key("inc_amount_txt"),
                )

            note = st.text_input("Obs (opcional)", key="inc_note")

            st.session_state.setdefault("last_income_key", None)

            if st.button("Salvar provento", type="primary", key="btn_save_income"):
                try:
                    amount = _parse_brl_decimal(amount_txt)
                except Exception:
                    st.error("Valor recebido inválido. Exemplo válido: 100,00")
                    st.stop()

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

                st.session_state["reset_income_form"] = True
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
        st.markdown("### Cotações automáticas")
        st.session_state.setdefault("quote_last_report", [])
        cset1, cset2 = st.columns([1.1, 1.1])
        with cset1:
            quote_timeout_s = st.number_input(
                "Timeout por ativo (s)",
                min_value=5,
                max_value=120,
                value=int(st.session_state.get("quote_timeout_s", 25)),
                step=1,
                key="quote_timeout_s",
            )
        with cset2:
            quote_workers = st.number_input(
                "Paralelismo",
                min_value=1,
                max_value=16,
                value=int(st.session_state.get("quote_workers", 4)),
                step=1,
                key="quote_workers",
            )

        if st.button("Atualizar cotação agora", key="btn_update_quotes"):
            try:
                assets = invest_repo.list_assets()
                total_assets = len(assets or [])
                if total_assets == 0:
                    st.warning("Nenhum ativo cadastrado para atualizar cotação.")
                    st.stop()

                st.caption("Busca em paralelo ativa. Ajuste timeout e paralelismo acima.")
                progress_bar = st.progress(0.0)
                progress_txt = st.empty()
                t0 = time.monotonic()

                def _on_progress(done: int, total: int, row: dict):
                    pct = done / max(total, 1)
                    progress_bar.progress(pct)
                    symbol = row.get("symbol") or "-"
                    progress_txt.caption(f"Consultando... {done}/{total} | último: {symbol}")

                report = invest_quotes.update_all_prices(
                    assets,
                    progress_cb=_on_progress,
                    timeout_s=float(quote_timeout_s),
                    max_workers=int(quote_workers),
                )
                elapsed_total = time.monotonic() - t0
                progress_bar.progress(1.0)
                progress_txt.caption(f"Concluído em {elapsed_total:.1f}s ({len(report)} ativos processados).")

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
                st.session_state["quote_last_report"] = report
                st.dataframe(pd.DataFrame(report), use_container_width=True)

            except Exception as e:
                st.error(f"Erro ao atualizar cotação: {e}")

        last_report = st.session_state.get("quote_last_report") or []
        pending_rows = [r for r in last_report if not r.get("ok")]
        if pending_rows:
            st.divider()
            st.markdown("### Pendentes de cotação (preenchimento manual)")
            manual_date = st.date_input(
                "Data para salvar as cotações manuais",
                key="pending_px_date",
                format="DD/MM/YYYY",
            )

            for r in pending_rows:
                asset_id = int(r.get("asset_id"))
                symbol = str(r.get("symbol") or "")
                err = str(r.get("error") or "Sem detalhe")
                key_px = f"pending_px_{asset_id}"
                key_btn = f"btn_save_pending_{asset_id}"

                c1, c2, c3, c4 = st.columns([1.2, 2.0, 1.0, 0.9])
                with c1:
                    st.write(f"**{symbol}**")
                with c2:
                    st.caption(err)
                with c3:
                    st.text_input(
                        "Preço",
                        value=st.session_state.get(key_px, ""),
                        placeholder="0,00",
                        key=key_px,
                        on_change=(lambda k=key_px: _mask_currency_input_key(k)),
                    )
                with c4:
                    if st.button("Salvar", key=key_btn):
                        try:
                            px_val = _parse_brl_decimal(st.session_state.get(key_px, ""))
                        except Exception:
                            st.error(f"{symbol}: preço inválido.")
                            st.stop()
                        if px_val <= 0:
                            st.error(f"{symbol}: preço deve ser maior que zero.")
                            st.stop()
                        invest_repo.upsert_price(
                            asset_id=asset_id,
                            date=manual_date.strftime("%Y-%m-%d"),
                            price=float(px_val),
                            source="manual",
                        )
                        st.success(f"{symbol}: cotação manual salva.")
                        st.rerun()

            if st.button("Salvar todos os preços preenchidos", key="btn_save_all_pending"):
                saved_manual = 0
                for r in pending_rows:
                    asset_id = int(r.get("asset_id"))
                    key_px = f"pending_px_{asset_id}"
                    raw_px = str(st.session_state.get(key_px, "") or "").strip()
                    if not raw_px:
                        continue
                    try:
                        px_val = _parse_brl_decimal(raw_px)
                    except Exception:
                        continue
                    if px_val <= 0:
                        continue
                    invest_repo.upsert_price(
                        asset_id=asset_id,
                        date=manual_date.strftime("%Y-%m-%d"),
                        price=float(px_val),
                        source="manual",
                    )
                    saved_manual += 1
                if saved_manual > 0:
                    st.success(f"Cotações manuais salvas: {saved_manual}.")
                    st.rerun()
                else:
                    st.warning("Nenhum preço válido preenchido para salvar.")

        st.divider()

        st.markdown("### Cadastrar cotação manual")
        if not assets:
            st.warning("Cadastre um ativo primeiro.")
        else:
            if st.session_state.get("reset_price_form", False):
                st.session_state["px_price_txt"] = ""
                st.session_state["reset_price_form"] = False

            c1, c2, c3 = st.columns([1.5, 1.0, 1.0])
            with c1:
                sym = st.selectbox("Ativo", list(asset_label.keys()), key="px_sym")
            with c2:
                px_date = st.date_input("Data", key="px_date", format="DD/MM/YYYY")
            with c3:
                price_txt = st.text_input(
                    "Cotação / PU / valor unit",
                    value=st.session_state.get("px_price_txt", ""),
                    placeholder="0,00",
                    key="px_price_txt",
                    on_change=lambda: _mask_currency_input_key("px_price_txt"),
                )

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
                try:
                    price = _parse_brl_decimal(price_txt)
                except Exception:
                    st.error("Cotação inválida. Exemplo válido: 12,34")
                    st.stop()
                invest_repo.upsert_price(asset_label[sym], px_date.strftime("%Y-%m-%d"), float(price), src.strip() if src.strip() else None)
                st.session_state["reset_price_form"] = True
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
                "asset_id","symbol","name","asset_class","sector","currency",
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
            if "sector" not in pos.columns:
                pos["sector"] = "Não definido"
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
                "symbol", "name", "asset_class", "sector",
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
                "sector": "Setor",
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

        st.markdown("#### Distribuição por setor")
        sector_chart = pos.copy()
        sector_chart["sector"] = sector_chart["sector"].fillna("Não definido")
        sector_chart["market_value_abs"] = sector_chart["market_value"].fillna(0.0)
        sector_chart = sector_chart.groupby("sector", as_index=False)["market_value_abs"].sum()
        sector_chart = sector_chart[sector_chart["market_value_abs"] > 0]
        if sector_chart.empty:
                st.info("Sem dados de mercado por setor ainda.")
        else:
                fig_sector = px.pie(sector_chart, names="sector", values="market_value_abs")
                st.plotly_chart(fig_sector, use_container_width=True)

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

        st.divider()
        st.markdown("#### Totais por setor")
        by_sector = pos.copy()
        by_sector["sector"] = by_sector["sector"].fillna("Não definido")
        by_sector = by_sector.groupby("sector", as_index=False).agg(
            invested=("cost_basis", "sum"),
            market=("market_value", "sum"),
            income=("income", "sum"),
            total_return=("total_return", "sum"),
        )
        by_sector["invested"] = by_sector["invested"].apply(to_brl)
        by_sector["market"] = by_sector["market"].apply(to_brl)
        by_sector["income"] = by_sector["income"].apply(to_brl)
        by_sector["total_return"] = by_sector["total_return"].apply(to_brl)
        st.dataframe(
            by_sector.rename(columns={
                "sector": "Setor",
                "invested": "Investido",
                "market": "Mercado",
                "income": "Proventos",
                "total_return": "Retorno Total",
            }),
            use_container_width=True,
            hide_index=True,
        )
