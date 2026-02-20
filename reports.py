# reports.py
import pandas as pd
from db import get_conn

def df_transactions(date_from: str | None = None, date_to: str | None = None):
    conn = get_conn()
    q = """
        SELECT
            t.id,
            t.date,
            t.description,
            t.amount_brl,
            ac.name AS account,
            c.name  AS category,
            c.kind  AS category_kind,
            t.method,
            t.notes
        FROM transactions t
        JOIN accounts ac ON ac.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE 1=1
    """
    params = []
    if date_from:
        q += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND t.date <= ?"
        params.append(date_to)

    q += " ORDER BY t.date ASC, t.id ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()

    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def kpis(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "saldo": 0.0}

    # Transferência não é Receita nem Despesa
    base = df[df["category_kind"].fillna("") != "Transferencia"].copy()

    receitas = float(base.loc[base["amount_brl"] > 0, "amount_brl"].sum())
    despesas = float(base.loc[base["amount_brl"] < 0, "amount_brl"].sum())  # negativo
    saldo = receitas + despesas

    return {"receitas": receitas, "despesas": despesas, "saldo": saldo}

def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    base = df[df["category_kind"].fillna("") != "Transferencia"].copy()

    base["month"] = base["date"].dt.to_period("M").astype(str)

    g = base.groupby("month", as_index=False).agg(
        receitas=("amount_brl", lambda s: float(s[s > 0].sum())),
        despesas=("amount_brl", lambda s: float(s[s < 0].sum())),
    )
    g["saldo"] = g["receitas"] + g["despesas"]
    return g

def category_expenses(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = df[df["category_kind"] == "Despesa"].copy()
    if d.empty:
        return pd.DataFrame()

    out = d.groupby("category", as_index=False)["amount"].sum()
    out["valor"] = out["amount"].abs()
    out = out.sort_values("valor", ascending=False)
    return out[["category", "valor"]]

def account_balance(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=["account", "saldo"])

    out = df.groupby("account")["amount_brl"].sum().reset_index().rename(columns={"amount_brl": "saldo"})
    out = out.sort_values("saldo", ascending=False)
    return out

def cash_balance_timeseries(date_from=None, date_to=None) -> pd.DataFrame:
    """
    Série diária do saldo acumulado (caixa) baseado nas transações.
    Retorna colunas: date, cash_balance
    """
    df = df_transactions(date_from, date_to)
    if df.empty:
        return pd.DataFrame(columns=["date", "cash_balance"])

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()

    daily = d.groupby("date")["amount_brl"].sum().reset_index()
    daily = daily.sort_values("date")
    daily["cash_balance"] = daily["amount_brl"].cumsum()
    return daily[["date", "cash_balance"]]
def account_balance_by_id(account_id: int) -> float:
    conn = get_conn()
    row = conn.execute("""
        SELECT COALESCE(SUM(amount_brl), 0)
        FROM transactions
        WHERE account_id = ?
    """, (account_id,)).fetchone()
    conn.close()
    if not row:
        return 0.0
    if isinstance(row, dict):
        return float(next(iter(row.values())) or 0.0)
    return float(row[0] or 0.0)
