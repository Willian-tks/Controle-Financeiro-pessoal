# invest_reports.py
import pandas as pd
import invest_repo
from db import get_conn

def _query_df(query: str, params: list | tuple | None = None) -> pd.DataFrame:
    conn = get_conn()
    rows = conn.execute(query, params or ()).fetchall()
    conn.close()
    return pd.DataFrame([dict(r) for r in rows])

def df_assets():
    df = _query_df("""
        SELECT id, symbol, name, asset_class, currency
        FROM assets
        ORDER BY asset_class, symbol
    """)
    return df

def df_trades(date_from=None, date_to=None):
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
    df = _query_df(q, params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def df_income(date_from=None, date_to=None):
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
    df = _query_df(q, params)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def df_latest_prices():
    df = _query_df("""
        SELECT p.asset_id, p.date AS price_date, p.price
        FROM prices p
        JOIN (
            SELECT asset_id, MAX(date) AS max_date
            FROM prices
            GROUP BY asset_id
        ) m ON m.asset_id = p.asset_id AND m.max_date = p.date
    """)
    return df

def positions_avg_cost(trades_df: pd.DataFrame):
    """
    MÃ©todo mÃ©dio:
    - MantÃ©m qty e cost_basis (custo total da posiÃ§Ã£o)
    - BUY: cost += qty*price + fees
    - SELL: realiza custo proporcional: cost -= avg_cost * qty_sold
    Retorna por asset: qty, avg_cost, cost_basis, realized_pnl (sem impostos), invested (compras lÃ­quidas)
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
                # venda sem posiÃ§Ã£o (deixa negativo; vocÃª pode bloquear no app depois)
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

    # ===== PreÃ§os (Ãºltimo preÃ§o por ativo) =====
    prices = df_latest_prices()
    if not prices.empty and not pos.empty:
        pos = pos.merge(
            prices[["asset_id", "price", "price_date"]],
            on="asset_id",
            how="left"
        )
    else:
        # garante colunas existirem mesmo sem preÃ§os
        pos["price"] = 0.0
        pos["price_date"] = None

    # garante preÃ§o numÃ©rico sempre
    pos["price"] = pd.to_numeric(pos.get("price", 0.0), errors="coerce").fillna(0.0)

    

    # ===== Dados do ativo (nome/moeda) =====
    assets = df_assets()
    if not assets.empty and not pos.empty:
        pos = pos.merge(
            assets.rename(columns={"id": "asset_id"})[["asset_id", "name", "currency"]],
            on="asset_id",
            how="left"
        )
    else:
        # se pos vazio, garante colunas para evitar erro no app
        if "name" not in pos.columns:
            pos["name"] = None
        if "currency" not in pos.columns:
            pos["currency"] = None

    # ===== CÃ¡lculos =====
    pos["market_value"] = pos["qty"] * pos["price"]
    pos["unrealized_pnl"] = pos["market_value"] - pos["cost_basis"]

    # ===== Proventos =====
    inc = df_income(date_from, date_to)
    if not inc.empty and not pos.empty:
        inc_sum = (
            inc.groupby("asset_id")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "income"})
        )
        pos = pos.merge(inc_sum, on="asset_id", how="left")

    # garante coluna income sempre
    if "income" not in pos.columns:
        pos["income"] = 0.0
    else:
        pos["income"] = pos["income"].fillna(0.0)

    return pos, tdf, inc
def df_prices_upto(up_to_date: str) -> pd.DataFrame:
    """
    Retorna o Ãºltimo preÃ§o conhecido (<= up_to_date) por ativo.
    up_to_date: 'YYYY-MM-DD'
    """
    df = _query_df("""
        SELECT p.asset_id, p.date AS price_date, p.price
        FROM prices p
        JOIN (
            SELECT asset_id, MAX(date) AS max_date
            FROM prices
            WHERE date <= ?
            GROUP BY asset_id
        ) m ON m.asset_id = p.asset_id AND m.max_date = p.date
    """, [up_to_date])
    return df


def investments_value_timeseries(date_from: str, date_to: str) -> pd.DataFrame:
    """
    SÃ©rie diÃ¡ria do valor de mercado dos investimentos entre date_from e date_to.
    Retorna colunas: date, invest_market_value
    """
    # trades do perÃ­odo (na prÃ¡tica, vocÃª precisa considerar posiÃ§Ãµes anteriores tambÃ©m,
    # mas para MVP vamos considerar tudo atÃ© date_to e filtrar por dia)
    tdf = df_trades(None, date_to)
    if tdf.empty:
        # retorna datas com 0
        dates = pd.date_range(date_from, date_to, freq="D")
        return pd.DataFrame({"date": dates, "invest_market_value": 0.0})

    # garante datetime
    tdf = tdf.copy()
    tdf["date"] = pd.to_datetime(tdf["date"])

    dates = pd.date_range(date_from, date_to, freq="D")
    out = []

    for d in dates:
        d_str = d.strftime("%Y-%m-%d")

        # trades atÃ© o dia D
        t_day = tdf[tdf["date"] <= d].copy()
        pos = positions_avg_cost(t_day)
        if pos.empty:
            out.append({"date": d, "invest_market_value": 0.0})
            continue

        prices = df_prices_upto(d_str)
        if not prices.empty:
            pos = pos.merge(prices[["asset_id", "price"]], on="asset_id", how="left")
        else:
            pos["price"] = 0.0

        pos["price"] = pd.to_numeric(pos["price"], errors="coerce").fillna(0.0)
        pos["market_value"] = pos["qty"] * pos["price"]

        out.append({"date": d, "invest_market_value": float(pos["market_value"].sum())})

    return pd.DataFrame(out)

# invest_reports.py
def fetch_last_price(asset: dict) -> float | None:
    def as_dict(x):
        return x if isinstance(x, dict) else dict(x)

    """
    Retorna o Ãºltimo preÃ§o do ativo ou None se nÃ£o conseguir.
    """
    asset = as_dict(asset)
    symbol = (asset.get("symbol") or "").strip().upper()
    aclass = (asset.get("asset_class") or "").strip().upper()

    # ===== AÃ‡Ã•ES/FIIs (B3) =====
    if aclass in ("AÃ‡Ã•ES BR", "ACOES BR", "STOCK_FII", "STOCK", "FII"):
        # yfinance usa .SA para B3
        ticker = symbol if symbol.endswith(".SA") else f"{symbol}.SA"

        import yfinance as yf
        t = yf.Ticker(ticker)
        h = t.history(period="1d")

        if h is None or h.empty:
            return None

        px = float(h["Close"].iloc[-1])
        return px if px > 0 else None

    # ===== CRIPTO =====
    if aclass == "CRYPTO":
        # Ex: BTC -> BTC-USD (vocÃª pode melhorar depois p/ BRL)
        ticker = symbol if "-" in symbol else f"{symbol}-USD"

        import yfinance as yf
        t = yf.Ticker(ticker)
        h = t.history(period="1d")

        if h is None or h.empty:
            return None

        px = float(h["Close"].iloc[-1])
        return px if px > 0 else None

    # ===== RENDA FIXA (sem fonte automÃ¡tica por enquanto) =====
    return None 
