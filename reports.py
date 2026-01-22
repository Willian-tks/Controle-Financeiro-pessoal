# reports.py
import pandas as pd
from db import get_conn

def df_transactions(date_from=None, date_to=None):
    conn = get_conn()
    q = """
        SELECT
            t.id, t.date, t.description, t.amount,
            a.name AS account,
            c.name AS category,
            COALESCE(c.kind, 'Sem Categoria') AS category_kind
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
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

    df = pd.read_sql_query(q, conn, params=params)
    conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M").astype(str)
    return df

def kpis(df: pd.DataFrame):
    if df.empty:
        return dict(receitas=0.0, despesas=0.0, saldo=0.0)

    receitas = df.loc[df["amount"] > 0, "amount"].sum()
    despesas = df.loc[df["amount"] < 0, "amount"].sum()  # negativo
    saldo = df["amount"].sum()
    return dict(receitas=float(receitas), despesas=float(despesas), saldo=float(saldo))

def monthly_summary(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=["month", "receitas", "despesas", "saldo"])

    g = df.groupby("month")["amount"].sum().reset_index().rename(columns={"amount": "saldo"})
    receitas = df[df["amount"] > 0].groupby("month")["amount"].sum().reset_index().rename(columns={"amount": "receitas"})
    despesas = df[df["amount"] < 0].groupby("month")["amount"].sum().reset_index().rename(columns={"amount": "despesas"})

    out = g.merge(receitas, on="month", how="left").merge(despesas, on="month", how="left")
    out["receitas"] = out["receitas"].fillna(0.0)
    out["despesas"] = out["despesas"].fillna(0.0)  # negativo
    out = out.sort_values("month")
    return out

def category_expenses(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=["category", "valor"])

    d = df[df["amount"] < 0].copy()
    if d.empty:
        return pd.DataFrame(columns=["category", "valor"])

    out = d.groupby("category")["amount"].sum().reset_index()
    out["valor"] = out["amount"].abs()
    out = out.drop(columns=["amount"]).sort_values("valor", ascending=False)
    out["category"] = out["category"].fillna("Sem Categoria")
    return out

def account_balance(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=["account", "saldo"])

    out = df.groupby("account")["amount"].sum().reset_index().rename(columns={"amount": "saldo"})
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

    daily = d.groupby("date")["amount"].sum().reset_index()
    daily = daily.sort_values("date")
    daily["cash_balance"] = daily["amount"].cumsum()
    return daily[["date", "cash_balance"]]