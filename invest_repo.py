# invest_repo.py
from db import get_conn

ASSET_CLASSES = ["STOCK_FII", "CRYPTO", "FIXED_INCOME"]
INCOME_TYPES = ["DIVIDEND", "JCP", "INTEREST", "COUPON"]

def list_assets():
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, ac.name AS broker_account
        FROM assets a
        LEFT JOIN accounts ac ON ac.id = a.broker_account_id
        ORDER BY a.asset_class, a.symbol
    """).fetchall()
    conn.close()
    return rows

def create_asset(symbol: str, name: str, asset_class: str, currency: str = "BRL",
                 broker_account_id=None, issuer=None, rate_type=None, rate_value=None, maturity_date=None):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO assets
        (symbol, name, asset_class, currency, broker_account_id, issuer, rate_type, rate_value, maturity_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (symbol.strip().upper(), name.strip(), asset_class, currency,
          broker_account_id, issuer, rate_type, rate_value, maturity_date))
    conn.commit()
    conn.close()

def delete_asset(asset_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM assets WHERE id=?", (int(asset_id),))
    conn.commit()
    conn.close()

def insert_trade(asset_id: int, date: str, side: str, quantity: float, price: float,
                 fees: float = 0.0, taxes: float = 0.0, note: str | None = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO trades(asset_id, date, side, quantity, price, fees, taxes, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (int(asset_id), date, side, float(quantity), float(price), float(fees), float(taxes), note))
    conn.commit()
    conn.close()

def list_trades(asset_id=None, date_from=None, date_to=None):
    conn = get_conn()
    q = """
        SELECT t.*, a.symbol, a.asset_class
        FROM trades t
        JOIN assets a ON a.id = t.asset_id
        WHERE 1=1
    """
    params = []
    if asset_id:
        q += " AND t.asset_id=?"
        params.append(int(asset_id))
    if date_from:
        q += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND t.date <= ?"
        params.append(date_to)

    q += " ORDER BY t.date DESC, t.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows

def delete_trade(trade_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM trades WHERE id=?", (int(trade_id),))
    conn.commit()
    conn.close()

def upsert_price(asset_id: int, date: str, price: float, source: str | None = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO prices(asset_id, date, price, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(asset_id, date) DO UPDATE SET
            price=excluded.price,
            source=excluded.source
    """, (int(asset_id), date, float(price), source))
    conn.commit()
    conn.close()

def latest_price(asset_id: int, up_to_date: str | None = None):
    conn = get_conn()
    if up_to_date:
        row = conn.execute("""
            SELECT date, price FROM prices
            WHERE asset_id=? AND date <= ?
            ORDER BY date DESC LIMIT 1
        """, (int(asset_id), up_to_date)).fetchone()
    else:
        row = conn.execute("""
            SELECT date, price FROM prices
            WHERE asset_id=?
            ORDER BY date DESC LIMIT 1
        """, (int(asset_id),)).fetchone()
    conn.close()
    return row

def insert_income(asset_id: int, date: str, type_: str, amount: float, note: str | None = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO income_events(asset_id, date, type, amount, note)
        VALUES (?, ?, ?, ?, ?)
    """, (int(asset_id), date, type_, float(amount), note))
    conn.commit()
    conn.close()

def list_income(asset_id=None, date_from=None, date_to=None):
    conn = get_conn()
    q = """
        SELECT i.*, a.symbol, a.asset_class
        FROM income_events i
        JOIN assets a ON a.id = i.asset_id
        WHERE 1=1
    """
    params = []
    if asset_id:
        q += " AND i.asset_id=?"
        params.append(int(asset_id))
    if date_from:
        q += " AND i.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND i.date <= ?"
        params.append(date_to)

    q += " ORDER BY i.date DESC, i.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows

def delete_income(income_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM income_events WHERE id=?", (int(income_id),))
    conn.commit()
    conn.close()

def get_asset(asset_id: int):
    conn = get_conn()
    row = conn.execute("""
        SELECT id, symbol, name, asset_class, broker_account_id
        FROM assets
        WHERE id = ?
    """, (int(asset_id),)).fetchone()
    conn.close()
    return row    