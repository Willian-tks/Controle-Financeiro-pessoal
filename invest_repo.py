# invest_repo.py
import sqlite3
from db import get_conn
from db import DB_PATH

ASSET_CLASSES = {
    "Ações BR": "ACAO_BR",
    "FIIs": "FII",
    "ETFs BR": "ETF_BR",
    "BDRs": "BDR",
    "Stocks US": "STOCK_US",
    "ETFs US": "ETF_US",
    "Cripto": "CRYPTO",
    "Renda Fixa": "RENDA_FIXA",
    "Caixa": "CAIXA",
    "Tesouro Direto": "TESOURO_DIRETO",
    "Fundos": "FUNDOS",
    "Coe": "COE",
    "Outros": "OUTROS",
}
INCOME_TYPES = {
    "Dividendos": "DIVIDEND",
    "JCP": "JCP",
    "Juros": "INTEREST",
    "Cupom": "COUPON",
    "Rend. RF": "RF_YIELD",
    "Aluguel (FII)": "FII_RENT",
}

def list_assets():
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            a.*,
            ac.name AS broker_account,
            sc.name AS source_account
        FROM assets a
        LEFT JOIN accounts ac ON ac.id = a.broker_account_id
        LEFT JOIN accounts sc ON sc.id = a.source_account_id
        ORDER BY a.asset_class, a.symbol
    """).fetchall()
    conn.close()
    return rows

def create_asset(
    symbol: str,
    name: str,
    asset_class: str,
    currency: str = "BRL",
    broker_account_id=None,
    source_account_id=None,
    issuer=None,
    rate_type=None,
    rate_value=None,
    maturity_date=None
):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO assets
        (symbol, name, asset_class, currency,
         broker_account_id, source_account_id,
         issuer, rate_type, rate_value, maturity_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol.strip().upper(),
        name.strip(),
        asset_class,
        currency,
        broker_account_id,
        source_account_id,
        issuer,
        rate_type,
        rate_value,
        maturity_date
    ))
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

#Esta linha foi criada para fazer deletes de lançamentos de teste durante a construção!!!!
def clear_invest_movements():
    conn = get_conn()
    c1 = conn.execute("DELETE FROM trades").rowcount
    c2 = conn.execute("DELETE FROM income_events").rowcount
    c3 = conn.execute("DELETE FROM prices").rowcount
    conn.commit()
    conn.close()
    return {"trades": c1, "income_events": c2, "prices": c3}

def clear_assets():
    """
    Remove TODOS os ativos.
    Requer que trades, income_events e prices já estejam vazios.
    """
    conn = get_conn()
    cur = conn.execute("DELETE FROM assets")
    conn.commit()
    conn.close()
    return cur.rowcount

def insert_price(asset_id: int, date: str, price: float, source: str = "yahoo"):
    """
    Salva (upsert) a cotação do ativo no dia.
    """
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO asset_prices (asset_id, date, price, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(asset_id, date, source)
        DO UPDATE SET price = excluded.price
        """,
        (int(asset_id), str(date), float(price), str(source)),
    )
    conn.commit()
    conn.close()


def get_last_price(asset_id: int):
    """
    Retorna a última cotação salva do ativo (row) ou None.
    """
    conn = get_conn()
    row = conn.execute(
        """
        SELECT asset_id, date, price, source
        FROM asset_prices
        WHERE asset_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 1
        """,
        (int(asset_id),),
    ).fetchone()
    conn.close()
    return row


def get_last_price_by_symbol(symbol: str):
    """
    Útil pro UI: busca a última cotação pelo symbol.
    """
    conn = get_conn()
    row = conn.execute(
        """
        SELECT p.asset_id, p.date, p.price, p.source, a.symbol
        FROM asset_prices p
        JOIN assets a ON a.id = p.asset_id
        WHERE UPPER(a.symbol) = UPPER(?)
        ORDER BY p.date DESC, p.id DESC
        LIMIT 1
        """,
        (symbol.strip(),),
    ).fetchone()
    conn.close()
    return row
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def upsert_quote(asset_id: int, px_date: str, price: float, src: str | None = None) -> None:
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO invest_quotes (asset_id, px_date, price, src)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(asset_id, px_date)
        DO UPDATE SET price=excluded.price, src=excluded.src
    """, (asset_id, px_date, float(price), src))
    conn.commit()
    conn.close()

def get_last_quote(asset_id: int):
    conn = _conn()
    row = conn.execute("""
        SELECT px_date, price, src
        FROM invest_quotes
        WHERE asset_id = ?
        ORDER BY px_date DESC
        LIMIT 1
    """, (asset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_asset(asset_id: int) -> tuple[bool, str]:
    from db import get_conn

    with get_conn() as conn:
        cur = conn.cursor()

        # verifica se há operações
        cur.execute("SELECT COUNT(*) FROM trades WHERE asset_id = ?", (asset_id,))
        trades_count = cur.fetchone()[0]

        # verifica se há cotações
        cur.execute("SELECT COUNT(*) FROM quotes WHERE asset_id = ?", (asset_id,))
        quotes_count = cur.fetchone()[0]

        if trades_count > 0 or quotes_count > 0:
            return False, "Ativo possui operações ou cotações registradas."

        cur.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        conn.commit()

    return True, "Ativo excluído com sucesso."

def update_asset(asset_id: int, symbol: str, name: str, asset_class: str,
                 currency: str, broker_account_id: int | None):

    from db import get_conn

    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            UPDATE assets
            SET symbol = ?, name = ?, asset_class = ?, currency = ?, broker_account_id = ?
            WHERE id = ?
        """, (symbol, name, asset_class, currency, broker_account_id, asset_id))

        conn.commit()

def get_asset_by_id(asset_id: int):
    from db import get_conn

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM assets
            WHERE id = ?
            """,
            (asset_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None