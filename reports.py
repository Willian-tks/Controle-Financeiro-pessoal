import pandas as pd

from db import get_conn
import repo
from tenant import get_current_user_id


def _uid(user_id: int | None = None) -> int:
    return int(user_id) if user_id is not None else int(get_current_user_id())


def _future_method_mask(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=bool)
    return (
        df["method"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"futuro", "agendado"})
    )


def _apply_future_visibility(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    d = df.copy()
    d["is_future_entry"] = _future_method_mask(d)
    today = pd.Timestamp.today().normalize()

    if mode == "futuro":
        # Compromissos: mostra todos (a vencer e vencidos), sem executar automaticamente.
        return d.loc[d["is_future_entry"]].copy()

    # Caixa/Competência: compromissos não entram até liquidação manual.
    keep = ~d["is_future_entry"]
    return d.loc[keep].copy()


def _df_transactions_cash(date_from: str | None = None, date_to: str | None = None, user_id: int | None = None):
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
        df["source_type"] = "transaction"
        df["charge_status"] = None
        df["invoice_period"] = None
        df["due_date"] = None
        df["card_name"] = None
        m = _future_method_mask(df)
        today = pd.Timestamp.today().normalize()
        df.loc[m & (df["date"] < today), "charge_status"] = "Vencido"
        df.loc[m & (df["date"] >= today), "charge_status"] = "Pendente"
    return df


def df_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: int | None = None,
    view: str = "caixa",
):
    mode = str(view or "caixa").strip().lower()
    if mode not in {"caixa", "competencia", "futuro"}:
        mode = "caixa"

    cash_df = _df_transactions_cash(date_from=date_from, date_to=date_to, user_id=user_id)
    cash_df = _apply_future_visibility(cash_df, mode)

    if mode == "futuro":
        cc_future_rows = repo.fetch_credit_charges_future(date_from=date_from, date_to=date_to, user_id=user_id) or []
        cc_future_df = pd.DataFrame([dict(r) for r in cc_future_rows])
        if not cc_future_df.empty:
            cc_future_df["date"] = pd.to_datetime(cc_future_df["date"])
            today = pd.Timestamp.today().normalize()
            cc_future_df = cc_future_df.loc[cc_future_df["date"] >= today].copy()
        if cash_df.empty and cc_future_df.empty:
            return pd.DataFrame()
        if cash_df.empty:
            return cc_future_df.sort_values(["date", "id"]).reset_index(drop=True)
        if cc_future_df.empty:
            return cash_df.sort_values(["date", "id"]).reset_index(drop=True)
        union_fut = pd.concat([cash_df, cc_future_df], ignore_index=True, sort=False)
        return union_fut.sort_values(["date", "id"]).reset_index(drop=True)

    if mode == "caixa":
        return cash_df

    if not cash_df.empty:
        keep_mask = ~(
            cash_df["description"].fillna("").str.startswith("PGTO FATURA ")
            | (cash_df["category"].fillna("") == "Fatura Cartão")
        )
        cash_df = cash_df.loc[keep_mask].copy()

    cc_rows = repo.fetch_credit_charges_competencia(date_from=date_from, date_to=date_to, user_id=user_id) or []
    cc_df = pd.DataFrame([dict(r) for r in cc_rows])
    if not cc_df.empty:
        cc_df["date"] = pd.to_datetime(cc_df["date"])

    if cash_df.empty and cc_df.empty:
        return pd.DataFrame()
    if cash_df.empty:
        return cc_df.sort_values(["date", "id"]).reset_index(drop=True)
    if cc_df.empty:
        return cash_df.sort_values(["date", "id"]).reset_index(drop=True)

    union = pd.concat([cash_df, cc_df], ignore_index=True, sort=False)
    return union.sort_values(["date", "id"]).reset_index(drop=True)


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
          AND UPPER(TRIM(COALESCE(method, ''))) NOT IN ('FUTURO', 'AGENDADO')
        """,
        (account_id, uid),
    ).fetchone()
    conn.close()
    return float(row["bal"] if row else 0.0)


def commitments_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    user_id: int | None = None,
) -> dict:
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT
            t.date,
            t.amount_brl,
            a.name AS account
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id AND a.user_id = t.user_id
        WHERE t.user_id = ?
          AND UPPER(TRIM(COALESCE(t.method, ''))) IN ('FUTURO', 'AGENDADO')
    """
    params: list = [uid]
    if date_from:
        q += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND t.date <= ?"
        params.append(date_to)
    if account:
        q += " AND a.name = ?"
        params.append(account)
    q += " ORDER BY t.date ASC, t.id ASC"

    rows = conn.execute(q, params).fetchall()
    conn.close()

    if not rows:
        return {"a_vencer": 0.0, "vencidos": 0.0}

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount_brl"] = pd.to_numeric(df["amount_brl"], errors="coerce").fillna(0.0)

    today = pd.Timestamp.today().normalize()
    a_vencer = float(df.loc[df["date"] >= today, "amount_brl"].abs().sum())
    vencidos = float(df.loc[df["date"] < today, "amount_brl"].abs().sum())

    # Compromissos em cartão ainda não faturados (futuros).
    cc_rows = repo.fetch_credit_charges_future(date_from=date_from, date_to=date_to, user_id=uid) or []
    if cc_rows:
        cdf = pd.DataFrame([dict(r) for r in cc_rows])
        cdf["date"] = pd.to_datetime(cdf["date"], errors="coerce")
        cdf["amount_brl"] = pd.to_numeric(cdf["amount_brl"], errors="coerce").fillna(0.0)
        if account:
            cdf = cdf.loc[cdf["account"].astype(str) == str(account)]
        cdf = cdf.loc[cdf["date"] >= today]
        a_vencer += float(cdf["amount_brl"].abs().sum())

    return {"a_vencer": a_vencer, "vencidos": vencidos}
