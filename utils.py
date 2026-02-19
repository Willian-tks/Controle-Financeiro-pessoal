# utils.py
import pandas as pd
import streamlit as st

def to_brl(x: float) -> str:
    # formatação simples pt-BR (sem depender de locale do SO)
    s = f"{x:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def normalize_import_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Espera colunas: date, description, amount, account, category (opcional), method (opcional), notes (opcional)
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"date", "description", "amount", "account"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV faltando colunas obrigatórias: {sorted(list(missing))}")

    # normalizações
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["description"] = df["description"].astype(str).str.strip()
    df["account"] = df["account"].astype(str).str.strip()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    for opt in ["category", "method", "notes"]:
        if opt not in df.columns:
            df[opt] = None
        else:
            df[opt] = df[opt].astype(str).replace({"nan": None}).where(df[opt].notna(), None)

    return df
def card(title: str, subtitle: str | None = None):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="muted">{subtitle}</div>', unsafe_allow_html=True)

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)

def badge(text: str, kind: str = "default"):
    cls = "badge"
    if kind == "ok":
        cls += " badge-ok"
    elif kind == "warn":
        cls += " badge-warn"
    elif kind == "bad":
        cls += " badge-bad"
    st.markdown(f'<span class="{cls}">{text}</span>', unsafe_allow_html=True)