import pandas as pd

from db import get_conn
from tenant import get_current_user_id


def _uid(user_id: int | None = None) -> int:
    return int(user_id) if user_id is not None else int(get_current_user_id())


def df_transactions(date_from: str | None = None, date_to: str | None = None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT
            t.id,
            t.date,
            t.description,
            t.amount_brl,
            ac.name AS account,
            c.name AS category,
            c.kind AS category_kind,
            t.method,
            t.notes
        FROM transactions t
        JOIN accounts ac ON ac.id = t.account_id AND ac.user_id = t.user_id
        LEFT JOIN categories c ON c.id = t.category_id AND c.user_id = t.user_id
        WHERE t.user_id = ?
    """
    params = [uid]
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

    base = df[df["category_kind"].fillna("") != "Transferencia"].copy()
    receitas = float(base.loc[base["amount_brl"] > 0, "amount_brl"].sum())
    despesas = float(base.loc[base["amount_brl"] < 0, "amount_brl"].sum())
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

    out = d.groupby("category", as_index=False)["amount_brl"].sum()
    out["valor"] = out["amount_brl"].abs()
    out = out.sort_values("valor", ascending=False)
    return out[["category", "valor"]]


def account_balance(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=["account", "saldo"])

    out = df.groupby("account")["amount_brl"].sum().reset_index().rename(columns={"amount_brl": "saldo"})
    out = out.sort_values("saldo", ascending=False)
    return out


def cash_balance_timeseries(date_from=None, date_to=None, user_id: int | None = None) -> pd.DataFrame:
    df = df_transactions(date_from, date_to, user_id=user_id)
    if df.empty:
        return pd.DataFrame(columns=["date", "cash_balance"])

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    daily = d.groupby("date")["amount_brl"].sum().reset_index()
    daily = daily.sort_values("date")
    daily["cash_balance"] = daily["amount_brl"].cumsum()
    return daily[["date", "cash_balance"]]


def account_balance_by_id(account_id: int, user_id: int | None = None) -> float:
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_brl), 0) AS bal
        FROM transactions
        WHERE account_id = ? AND user_id = ?
        """,
        (account_id, uid),
    ).fetchone()
    conn.close()
    return float(row["bal"] if row else 0.0)
