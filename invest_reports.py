# invest_reports.py
import pandas as pd
from db import get_conn

def df_assets():
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT id, symbol, name, asset_class, currency
        FROM assets
        ORDER BY asset_class, symbol
    """, conn)
    conn.close()
    return df

def df_trades(date_from=None, date_to=None):
    conn = get_conn()
    q = """
        SELECT t.id, t.asset_id, t.date, t.side, t.quantity, t.price, t.fees, t.taxes,
               a.symbol, a.asset_class
        FROM trades t
        JOIN assets a ON a.id = t.asset_id
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
    return df

def df_income(date_from=None, date_to=None):
    conn = get_conn()
    q = """
        SELECT i.id, i.asset_id, i.date, i.type, i.amount,
               a.symbol, a.asset_class
        FROM income_events i
        JOIN assets a ON a.id = i.asset_id
        WHERE 1=1
    """
    params = []
    if date_from:
        q += " AND i.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND i.date <= ?"
        params.append(date_to)
    q += " ORDER BY i.date ASC, i.id ASC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def df_latest_prices():
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT p.asset_id, p.date, p.price
        FROM prices p
        JOIN (
            SELECT asset_id, MAX(date) AS max_date
            FROM prices
            GROUP BY asset_id
        ) m ON m.asset_id = p.asset_id AND m.max_date = p.date
    """, conn)
    conn.close()
    return df

def positions_avg_cost(trades_df: pd.DataFrame):
    """
    Método médio:
    - Mantém qty e cost_basis (custo total da posição)
    - BUY: cost += qty*price + fees
    - SELL: realiza custo proporcional: cost -= avg_cost * qty_sold
    Retorna por asset: qty, avg_cost, cost_basis, realized_pnl (sem impostos), invested (compras líquidas)
    """
    if trades_df.empty:
        return pd.DataFrame(columns=["asset_id", "symbol", "asset_class", "qty", "avg_cost", "cost_basis", "realized_pnl"])

    trades_df = trades_df.sort_values(["date", "id"]).copy()

    state = {}  # asset_id -> dict
    rows = []

    for _, r in trades_df.iterrows():
        aid = int(r["asset_id"])
        sym = r["symbol"]
        cls = r["asset_class"]
        side = r["side"]
        qty = float(r["quantity"])
        price = float(r["price"])
        fees = float(r["fees"] or 0.0)
        taxes = float(r["taxes"] or 0.0)

        if aid not in state:
            state[aid] = dict(symbol=sym, asset_class=cls, qty=0.0, cost_basis=0.0, realized_pnl=0.0)

        s = state[aid]
        if side == "BUY":
            s["qty"] += qty
            s["cost_basis"] += qty * price + fees
        else:  # SELL
            if s["qty"] <= 0:
                # venda sem posição (deixa negativo; você pode bloquear no app depois)
                avg_cost = 0.0
            else:
                avg_cost = s["cost_basis"] / s["qty"] if s["qty"] != 0 else 0.0

            proceeds = qty * price - fees - taxes
            cost_removed = avg_cost * qty
            s["realized_pnl"] += proceeds - cost_removed

            s["qty"] -= qty
            s["cost_basis"] -= cost_removed

        state[aid] = s

    for aid, s in state.items():
        qty = s["qty"]
        avg_cost = (s["cost_basis"] / qty) if qty else 0.0
        rows.append({
            "asset_id": aid,
            "symbol": s["symbol"],
            "asset_class": s["asset_class"],
            "qty": qty,
            "avg_cost": avg_cost,
            "cost_basis": s["cost_basis"],
            "realized_pnl": s["realized_pnl"],
        })

    return pd.DataFrame(rows)

def portfolio_view(date_from=None, date_to=None):
    tdf = df_trades(date_from, date_to)
    pos = positions_avg_cost(tdf)

    prices = df_latest_prices()
    if not prices.empty and not pos.empty:
        pos = pos.merge(prices[["asset_id", "price"]], on="asset_id", how="left")
    else:
        pos["price"] = None

    # market value e pnl não realizado
    pos["market_value"] = pos["qty"] * pos["price"].fillna(0.0)
    pos["unrealized_pnl"] = pos["market_value"] - pos["cost_basis"]

    # proventos
    inc = df_income(date_from, date_to)
    if not inc.empty:
        inc_sum = inc.groupby("asset_id")["amount"].sum().reset_index().rename(columns={"amount": "income"})
        pos = pos.merge(inc_sum, on="asset_id", how="left")
    # garante coluna income sempre
    if "income" not in pos.columns:
        pos["income"] = 0.0
    else:
        pos["income"] = pos["income"].fillna(0.0)

    return pos, tdf, inc