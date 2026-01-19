# utils.py
import pandas as pd

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