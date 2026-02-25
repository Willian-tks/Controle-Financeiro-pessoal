import pandas as pd

from db import get_conn
from tenant import get_current_user_id


def _uid(user_id: int | None = None) -> int:
    return int(user_id) if user_id is not None else int(get_current_user_id())


def _query_df(query: str, params: list | tuple | None = None) -> pd.DataFrame:
    conn = get_conn()
    rows = conn.execute(query, params or ()).fetchall()
    conn.close()
    return pd.DataFrame([dict(r) for r in rows])


def df_assets(user_id: int | None = None):
    uid = _uid(user_id)
    return _query_df(
        """
        SELECT id, symbol, name, asset_class, sector, currency
        FROM assets
        WHERE user_id = ?
        ORDER BY asset_class, symbol
        """,
        [uid],
    )


def df_trades(date_from=None, date_to=None, user_id: int | None = None):
    uid = _uid(user_id)
    q = """
        SELECT t.id, t.asset_id, t.date, t.side, t.quantity, t.price, t.exchange_rate, t.fees, t.taxes,
               a.symbol, a.asset_class, a.currency
        FROM trades t
        JOIN assets a ON a.id = t.asset_id AND a.user_id = t.user_id
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
    df = _query_df(q, params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def df_income(date_from=None, date_to=None, user_id: int | None = None):
    uid = _uid(user_id)
    q = """
        SELECT i.id, i.asset_id, i.date, i.type, i.amount,
               a.symbol, a.asset_class
        FROM income_events i
        JOIN assets a ON a.id = i.asset_id AND a.user_id = i.user_id
        WHERE i.user_id = ?
    """
    params = [uid]
    if date_from:
        q += " AND i.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND i.date <= ?"
        params.append(date_to)
    q += " ORDER BY i.date ASC, i.id ASC"
    df = _query_df(q, params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def df_latest_prices(user_id: int | None = None):
    uid = _uid(user_id)
    return _query_df(
        """
        SELECT p.asset_id, p.date AS price_date, p.price
        FROM prices p
        JOIN (
            SELECT asset_id, MAX(date) AS max_date
            FROM prices
            WHERE user_id = ?
            GROUP BY asset_id
        ) m ON m.asset_id = p.asset_id AND m.max_date = p.date
        WHERE p.user_id = ?
        """,
        [uid, uid],
    )


def positions_avg_cost(trades_df: pd.DataFrame):
    if trades_df.empty:
        return pd.DataFrame(columns=["asset_id", "symbol", "asset_class", "qty", "avg_cost", "cost_basis", "realized_pnl"])

    trades_df = trades_df.sort_values(["date", "id"]).copy()
    state = {}
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
        exchange_rate = float(r.get("exchange_rate") or 1.0)
        is_usd = str(r.get("currency") or "").strip().upper() == "USD"
        fx = exchange_rate if is_usd and exchange_rate > 0 else 1.0
        gross_brl = qty * price * fx
        fees_brl = fees * fx if is_usd else fees
        taxes_brl = taxes * fx if is_usd else taxes

        if aid not in state:
            state[aid] = dict(symbol=sym, asset_class=cls, qty=0.0, cost_basis=0.0, realized_pnl=0.0, last_fx=1.0)

        s = state[aid]
        s["last_fx"] = fx
        if side == "BUY":
            s["qty"] += qty
            s["cost_basis"] += gross_brl + fees_brl + taxes_brl
        else:
            if s["qty"] <= 0:
                avg_cost = 0.0
            else:
                avg_cost = s["cost_basis"] / s["qty"] if s["qty"] != 0 else 0.0

            proceeds = gross_brl - fees_brl - taxes_brl
            cost_removed = avg_cost * qty
            s["realized_pnl"] += proceeds - cost_removed
            s["qty"] -= qty
            s["cost_basis"] -= cost_removed

        state[aid] = s

    for aid, s in state.items():
        qty = s["qty"]
        avg_cost = (s["cost_basis"] / qty) if qty else 0.0
        rows.append(
            {
                "asset_id": aid,
                "symbol": s["symbol"],
                "asset_class": s["asset_class"],
                "qty": qty,
                "avg_cost": avg_cost,
                "cost_basis": s["cost_basis"],
                "realized_pnl": s["realized_pnl"],
                "last_fx": s["last_fx"],
            }
        )

    return pd.DataFrame(rows)


def portfolio_view(date_from=None, date_to=None, user_id: int | None = None):
    uid = _uid(user_id)
    tdf = df_trades(date_from, date_to, user_id=uid)
    pos = positions_avg_cost(tdf)

    prices = df_latest_prices(user_id=uid)
    if not prices.empty and not pos.empty:
        pos = pos.merge(prices[["asset_id", "price", "price_date"]], on="asset_id", how="left")
    else:
        pos["price"] = 0.0
        pos["price_date"] = None

    pos["price"] = pd.to_numeric(pos.get("price", 0.0), errors="coerce").fillna(0.0)

    assets = df_assets(user_id=uid)
    if not assets.empty and not pos.empty:
        pos = pos.merge(
            assets.rename(columns={"id": "asset_id"})[["asset_id", "name", "sector", "currency"]],
            on="asset_id",
            how="left",
        )
    else:
        if "name" not in pos.columns:
            pos["name"] = None
        if "sector" not in pos.columns:
            pos["sector"] = None
        if "currency" not in pos.columns:
            pos["currency"] = None

    fx = pd.to_numeric(pos.get("last_fx", 1.0), errors="coerce").fillna(1.0)
    is_usd_asset = pos.get("currency", "").astype(str).str.upper().eq("USD")
    fx_factor = fx.where(is_usd_asset, 1.0)
    pos["market_value"] = pos["qty"] * pos["price"] * fx_factor
    pos["unrealized_pnl"] = pos["market_value"] - pos["cost_basis"]

    inc = df_income(date_from, date_to, user_id=uid)
    if not inc.empty and not pos.empty:
        inc_sum = inc.groupby("asset_id")["amount"].sum().reset_index().rename(columns={"amount": "income"})
        pos = pos.merge(inc_sum, on="asset_id", how="left")

    if "income" not in pos.columns:
        pos["income"] = 0.0
    else:
        pos["income"] = pos["income"].fillna(0.0)

    return pos, tdf, inc


def df_prices_upto(up_to_date: str, user_id: int | None = None) -> pd.DataFrame:
    uid = _uid(user_id)
    return _query_df(
        """
        SELECT p.asset_id, p.date AS price_date, p.price
        FROM prices p
        JOIN (
            SELECT asset_id, MAX(date) AS max_date
            FROM prices
            WHERE user_id = ? AND date <= ?
            GROUP BY asset_id
        ) m ON m.asset_id = p.asset_id AND m.max_date = p.date
        WHERE p.user_id = ?
        """,
        [uid, up_to_date, uid],
    )


def investments_value_timeseries(date_from: str, date_to: str, user_id: int | None = None) -> pd.DataFrame:
    uid = _uid(user_id)
    tdf = df_trades(None, date_to, user_id=uid)
    if tdf.empty:
        dates = pd.date_range(date_from, date_to, freq="D")
        return pd.DataFrame({"date": dates, "invest_market_value": 0.0})

    tdf = tdf.copy()
    tdf["date"] = pd.to_datetime(tdf["date"])
    dates = pd.date_range(date_from, date_to, freq="D")
    out = []

    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        t_day = tdf[tdf["date"] <= d].copy()
        pos = positions_avg_cost(t_day)
        if pos.empty:
            out.append({"date": d, "invest_market_value": 0.0})
            continue

        prices = df_prices_upto(d_str, user_id=uid)
        if not prices.empty:
            pos = pos.merge(prices[["asset_id", "price"]], on="asset_id", how="left")
        else:
            pos["price"] = 0.0

        pos["price"] = pd.to_numeric(pos["price"], errors="coerce").fillna(0.0)
        pos["market_value"] = pos["qty"] * pos["price"]
        out.append({"date": d, "invest_market_value": float(pos["market_value"].sum())})

    return pd.DataFrame(out)
