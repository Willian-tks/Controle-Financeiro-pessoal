from db import get_conn
from tenant import get_current_user_id, get_current_workspace_id
import re
from contextvars import ContextVar

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

ASSET_SECTORS = [
    "Não definido",
    "Financeiro",
    "Energia & Utilidades",
    "Commodities",
    "Consumo",
    "Indústria",
    "Serviços",
    "Tecnologia & Telecom",
    "Imobiliário",
]

INCOME_TYPES = {
    "Dividendos": "DIVIDEND",
    "JCP": "JCP",
    "Juros": "INTEREST",
    "Cupom": "COUPON",
    "Rend. RF": "RF_YIELD",
    "Aluguel (FII)": "FII_RENT",
}


_UNSET = object()
_USE_WORKSPACE_SCOPE: ContextVar[bool] = ContextVar("invest_repo_use_workspace_scope", default=False)


def _uid(user_id: int | None = None) -> int:
    wid = get_current_workspace_id(required=False)
    if wid is not None:
        _USE_WORKSPACE_SCOPE.set(True)
        return int(wid)

    uid = int(user_id) if user_id is not None else int(get_current_user_id())
    conn = get_conn()
    try:
        row = _exec(conn, 
            """
            SELECT wu.workspace_id
            FROM workspace_users wu
            JOIN workspaces w ON w.id = wu.workspace_id
            WHERE wu.user_id = ?
            ORDER BY
                CASE WHEN LOWER(COALESCE(w.status, 'active')) = 'active' THEN 0 ELSE 1 END,
                CASE WHEN UPPER(COALESCE(wu.role, '')) = 'OWNER' THEN 0 ELSE 1 END,
                wu.workspace_id
            LIMIT 1
            """,
            (uid,),
            rewrite_scope=False,
        ).fetchone()
    except Exception:
        row = None
    finally:
        conn.close()

    if not row:
        _USE_WORKSPACE_SCOPE.set(False)
        return uid
    _USE_WORKSPACE_SCOPE.set(True)
    try:
        return int(row["workspace_id"])
    except Exception:
        return int(row[0])


def _scope_sql(query: str) -> str:
    return re.sub(r"(?<![A-Za-z0-9_])user_id(?![A-Za-z0-9_])", "workspace_id", str(query))


def _exec(conn, query: str, params: tuple | list | None = None, rewrite_scope: bool | None = None):
    use_workspace = _USE_WORKSPACE_SCOPE.get() if rewrite_scope is None else bool(rewrite_scope)
    q = _scope_sql(query) if use_workspace else str(query)
    return conn.execute(q, tuple(params or ()))


def _cur_exec(cur, query: str, params: tuple | list | None = None, rewrite_scope: bool | None = None):
    use_workspace = _USE_WORKSPACE_SCOPE.get() if rewrite_scope is None else bool(rewrite_scope)
    q = _scope_sql(query) if use_workspace else str(query)
    cur.execute(q, tuple(params or ()))
    return cur


def _norm_asset_class(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return "_".join(raw.split())


def list_assets(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    rows = _exec(conn, 
        """
        SELECT
            a.*,
            ac.name AS broker_account,
            sc.name AS source_account
        FROM assets a
        LEFT JOIN accounts ac ON ac.id = a.broker_account_id AND ac.user_id = a.user_id
        LEFT JOIN accounts sc ON sc.id = a.source_account_id AND sc.user_id = a.user_id
        WHERE a.user_id = ?
        ORDER BY a.asset_class, a.symbol
        """,
        (uid,),
    ).fetchall()
    conn.close()
    return rows


def create_asset(
    symbol: str,
    name: str,
    asset_class: str,
    sector: str | None = None,
    currency: str = "BRL",
    broker_account_id=None,
    source_account_id=None,
    issuer=None,
    rate_type=None,
    rate_value=None,
    maturity_date=None,
    rentability_type=None,
    index_name=None,
    index_pct=None,
    spread_rate=None,
    fixed_rate=None,
    principal_amount=None,
    current_value=None,
    last_update=None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    exists = _exec(conn, 
        "SELECT id FROM assets WHERE user_id = ? AND UPPER(symbol) = UPPER(?)",
        (uid, symbol.strip().upper()),
    ).fetchone()
    created = False
    if not exists:
        _exec(conn, 
            """
            INSERT INTO assets
            (
                symbol, name, asset_class, sector, currency, broker_account_id, source_account_id,
                issuer, rate_type, rate_value, maturity_date, rentability_type, index_name,
                index_pct, spread_rate, fixed_rate, principal_amount, current_value, last_update, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol.strip().upper(),
                name.strip(),
                asset_class,
                sector if sector else "Não definido",
                currency,
                broker_account_id,
                source_account_id,
                issuer,
                rate_type,
                rate_value,
                maturity_date,
                rentability_type,
                index_name,
                index_pct,
                spread_rate,
                fixed_rate,
                principal_amount,
                current_value,
                last_update,
                uid,
            ),
        )
        created = True
    conn.commit()
    conn.close()
    return created


def insert_trade(
    asset_id: int,
    date: str,
    side: str,
    quantity: float,
    price: float,
    exchange_rate: float = 1.0,
    fees: float = 0.0,
    taxes: float = 0.0,
    note: str | None = None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, 
        """
        INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, note, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(asset_id),
            date,
            side,
            float(quantity),
            float(price),
            float(exchange_rate or 1.0),
            float(fees),
            float(taxes),
            note,
            uid,
        ),
    )
    conn.commit()
    conn.close()


def list_trades(asset_id=None, date_from=None, date_to=None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT t.*, a.symbol, a.asset_class
        FROM trades t
        JOIN assets a ON a.id = t.asset_id AND a.user_id = t.user_id
        WHERE t.user_id = ?
    """
    params = [uid]
    if asset_id:
        q += " AND t.asset_id = ?"
        params.append(int(asset_id))
    if date_from:
        q += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND t.date <= ?"
        params.append(date_to)

    q += " ORDER BY t.date DESC, t.id DESC"
    rows = _exec(conn, q, params).fetchall()
    conn.close()
    return rows


def delete_trade(trade_id: int, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, "DELETE FROM trades WHERE id = ? AND user_id = ?", (int(trade_id), uid))
    conn.commit()
    conn.close()


def delete_trade_with_cash_reversal(trade_id: int, user_id: int | None = None) -> tuple[bool, str]:
    uid = _uid(user_id)
    conn = get_conn()
    try:
        trade = _exec(conn, 
            """
            SELECT
                t.id, t.asset_id, t.date, t.side, t.quantity, t.price, t.exchange_rate, t.fees, t.taxes, t.note,
                a.symbol, a.broker_account_id, a.currency, a.asset_class
            FROM trades t
            JOIN assets a ON a.id = t.asset_id AND a.user_id = t.user_id
            WHERE t.id = ? AND t.user_id = ?
            """,
            (int(trade_id), uid),
        ).fetchone()

        if not trade:
            return False, "Operação não encontrada."

        broker_account_id = trade["broker_account_id"]
        if not broker_account_id:
            return False, "Ativo sem conta corretora vinculada. Não é possível reverter o caixa da operação."

        qty = float(trade["quantity"] or 0.0)
        price = float(trade["price"] or 0.0)
        exchange_rate = float(trade["exchange_rate"] or 1.0)
        fees = float(trade["fees"] or 0.0)
        taxes = float(trade["taxes"] or 0.0)
        side = str(trade["side"] or "").upper()
        is_usd = str(trade["currency"] or "").strip().upper() == "USD"
        symbol = str(trade["symbol"] or "").strip().upper()
        note = (str(trade["note"]).strip() if trade["note"] is not None else "")

        fx = exchange_rate if is_usd and exchange_rate > 0 else 1.0
        gross = qty * price * fx
        fees_brl = fees * fx if is_usd else fees
        taxes_brl = taxes * fx if is_usd else taxes
        is_fixed_income = _norm_asset_class(str(trade["asset_class"] or "")) in {"renda_fixa", "tesouro_direto", "coe", "fundos"}
        if side == "BUY":
            if is_fixed_income:
                target_amount = -(gross + fees_brl)
                # Compatibilidade com lançamentos antigos que subtraíam imposto na aplicação.
                target_amount_alt = -(gross + fees_brl - taxes_brl)
            else:
                target_amount = -(gross + fees_brl + taxes_brl)
                target_amount_alt = target_amount
            if target_amount > 0:
                target_amount = 0.0
            desc = f"INV BUY {symbol}"
        else:
            target_amount = +(gross - fees_brl - taxes_brl)
            target_amount_alt = +(gross - fees_brl)
            desc = f"INV SELL {symbol}"

        tx_rows = _exec(conn, 
            """
            SELECT id, amount_brl, notes
            FROM transactions
            WHERE user_id = ?
              AND date = ?
              AND account_id = ?
              AND method = 'INV'
              AND description = ?
            ORDER BY id DESC
            """,
            (uid, trade["date"], int(broker_account_id), desc),
        ).fetchall()

        chosen_tx_id = None
        for tx in tx_rows:
            tx_amount = float(tx["amount_brl"] or 0.0)
            tx_note = (str(tx["notes"]).strip() if tx["notes"] is not None else "")
            if (abs(tx_amount - target_amount) < 1e-6 or abs(tx_amount - target_amount_alt) < 1e-6) and tx_note == note:
                chosen_tx_id = int(tx["id"])
                break

        if chosen_tx_id is None:
            for tx in tx_rows:
                tx_amount = float(tx["amount_brl"] or 0.0)
                if abs(tx_amount - target_amount) < 1e-6 or abs(tx_amount - target_amount_alt) < 1e-6:
                    chosen_tx_id = int(tx["id"])
                    break

        if chosen_tx_id is None:
            reverse_amount = -target_amount
            _exec(conn, 
                """
                INSERT INTO transactions(date, description, amount_brl, account_id, category_id, method, notes, user_id)
                VALUES (?, ?, ?, ?, NULL, 'INV', ?, ?)
                """,
                (
                    str(trade["date"]),
                    f"INV REVERSAL {symbol}",
                    float(reverse_amount),
                    int(broker_account_id),
                    f"Reversão automática da operação {int(trade_id)} (lançamento original não encontrado).",
                    uid,
                ),
            )
            _exec(conn, "DELETE FROM trades WHERE id = ? AND user_id = ?", (int(trade_id), uid))
            conn.commit()
            return True, "Operação excluída e saldo da corretora ajustado por lançamento compensatório."

        _exec(conn, "DELETE FROM transactions WHERE id = ? AND user_id = ?", (chosen_tx_id, uid))
        _exec(conn, "DELETE FROM trades WHERE id = ? AND user_id = ?", (int(trade_id), uid))
        conn.commit()
        return True, "Operação excluída e saldo da corretora ajustado."
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao excluir operação: {e}"
    finally:
        conn.close()


def upsert_price(asset_id: int, date: str, price: float, source: str | None = None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, 
        """
        INSERT INTO prices(asset_id, date, price, source, user_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(asset_id, date) DO UPDATE SET
            price=excluded.price,
            source=excluded.source
        """,
        (int(asset_id), date, float(price), source, uid),
    )
    conn.commit()
    conn.close()


def latest_price(asset_id: int, up_to_date: str | None = None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    if up_to_date:
        row = _exec(conn, 
            """
            SELECT date, price FROM prices
            WHERE user_id = ? AND asset_id = ? AND date <= ?
            ORDER BY date DESC LIMIT 1
            """,
            (uid, int(asset_id), up_to_date),
        ).fetchone()
    else:
        row = _exec(conn, 
            """
            SELECT date, price FROM prices
            WHERE user_id = ? AND asset_id = ?
            ORDER BY date DESC LIMIT 1
            """,
            (uid, int(asset_id)),
        ).fetchone()
    conn.close()
    return row


def list_prices(asset_id: int | None = None, limit: int = 200, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT p.id, p.asset_id, p.date, p.price, p.source, a.symbol, a.asset_class
        FROM prices p
        JOIN assets a ON a.id = p.asset_id AND a.user_id = p.user_id
        WHERE p.user_id = ?
    """
    params: list = [uid]
    if asset_id is not None:
        q += " AND p.asset_id = ?"
        params.append(int(asset_id))
    q += " ORDER BY p.date DESC, p.id DESC LIMIT ?"
    params.append(int(limit))
    rows = _exec(conn, q, params).fetchall()
    conn.close()
    return rows


def insert_income(asset_id: int, date: str, type_: str, amount: float, note: str | None = None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, 
        """
        INSERT INTO income_events(asset_id, date, type, amount, note, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(asset_id), date, type_, float(amount), note, uid),
    )
    conn.commit()
    conn.close()


def list_income(asset_id=None, date_from=None, date_to=None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT i.*, a.symbol, a.asset_class
        FROM income_events i
        JOIN assets a ON a.id = i.asset_id AND a.user_id = i.user_id
        WHERE i.user_id = ?
    """
    params = [uid]
    if asset_id:
        q += " AND i.asset_id = ?"
        params.append(int(asset_id))
    if date_from:
        q += " AND i.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND i.date <= ?"
        params.append(date_to)

    q += " ORDER BY i.date DESC, i.id DESC"
    rows = _exec(conn, q, params).fetchall()
    conn.close()
    return rows


def delete_income(income_id: int, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, "DELETE FROM income_events WHERE id = ? AND user_id = ?", (int(income_id), uid))
    conn.commit()
    conn.close()


def get_asset(asset_id: int, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    row = _exec(conn, 
        """
        SELECT id, symbol, name, asset_class, sector, broker_account_id, source_account_id
        FROM assets
        WHERE id = ? AND user_id = ?
        """,
        (int(asset_id), uid),
    ).fetchone()
    conn.close()
    return row


def clear_invest_movements(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    c1 = _exec(conn, "DELETE FROM trades WHERE user_id = ?", (uid,)).rowcount
    c2 = _exec(conn, "DELETE FROM income_events WHERE user_id = ?", (uid,)).rowcount
    c3 = _exec(conn, "DELETE FROM prices WHERE user_id = ?", (uid,)).rowcount
    conn.commit()
    conn.close()
    return {"trades": c1, "income_events": c2, "prices": c3}


def clear_assets(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    cur = _exec(conn, "DELETE FROM assets WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    return cur.rowcount


def insert_price(asset_id: int, date: str, price: float, source: str = "yahoo", user_id: int | None = None):
    upsert_price(int(asset_id), str(date), float(price), str(source), user_id=user_id)


def get_last_price(asset_id: int, user_id: int | None = None):
    return latest_price(int(asset_id), user_id=user_id)


def get_last_price_by_symbol(symbol: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    row = _exec(conn, 
        """
        SELECT p.asset_id, p.date AS date, p.price, p.source, a.symbol
        FROM prices p
        JOIN assets a ON a.id = p.asset_id AND a.user_id = p.user_id
        WHERE p.user_id = ? AND UPPER(a.symbol) = UPPER(?)
        ORDER BY p.date DESC, p.id DESC
        LIMIT 1
        """,
        (uid, symbol.strip()),
    ).fetchone()
    conn.close()
    return row


def delete_asset(asset_id: int, user_id: int | None = None) -> tuple[bool, str]:
    uid = _uid(user_id)
    with get_conn() as conn:
        cur = conn.cursor()

        _cur_exec(cur, 
            "SELECT COUNT(*) AS n FROM trades WHERE asset_id = ? AND user_id = ?",
            (asset_id, uid),
        )
        trades_row = cur.fetchone()
        trades_count = int((trades_row["n"] if isinstance(trades_row, dict) else trades_row[0]) or 0)

        _cur_exec(cur, 
            "SELECT COUNT(*) AS n FROM income_events WHERE asset_id = ? AND user_id = ?",
            (asset_id, uid),
        )
        income_row = cur.fetchone()
        income_count = int((income_row["n"] if isinstance(income_row, dict) else income_row[0]) or 0)

        if trades_count > 0 or income_count > 0:
            return False, f"Ativo possui movimentações registradas (trades: {trades_count}, proventos: {income_count})."

        _cur_exec(cur, "DELETE FROM prices WHERE asset_id = ? AND user_id = ?", (asset_id, uid))
        _cur_exec(cur, "DELETE FROM assets WHERE id = ? AND user_id = ?", (asset_id, uid))
        conn.commit()

    return True, "Ativo excluído com sucesso."


def update_asset(
    asset_id: int,
    symbol: str,
    name: str,
    asset_class: str,
    sector: str,
    currency: str,
    broker_account_id: int | None,
    source_account_id: int | None | object = _UNSET,
    issuer: str | None | object = _UNSET,
    rate_type: str | None | object = _UNSET,
    rate_value: float | None | object = _UNSET,
    maturity_date: str | None | object = _UNSET,
    rentability_type: str | None | object = _UNSET,
    index_name: str | None | object = _UNSET,
    index_pct: float | None | object = _UNSET,
    spread_rate: float | None | object = _UNSET,
    fixed_rate: float | None | object = _UNSET,
    principal_amount: float | None | object = _UNSET,
    current_value: float | None | object = _UNSET,
    last_update: str | None | object = _UNSET,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        updates = [
            "symbol = ?",
            "name = ?",
            "asset_class = ?",
            "sector = ?",
            "currency = ?",
            "broker_account_id = ?",
        ]
        params: list = [symbol, name, asset_class, sector, currency, broker_account_id]

        optional_fields = [
            ("source_account_id", source_account_id),
            ("issuer", issuer),
            ("rate_type", rate_type),
            ("rate_value", rate_value),
            ("maturity_date", maturity_date),
            ("rentability_type", rentability_type),
            ("index_name", index_name),
            ("index_pct", index_pct),
            ("spread_rate", spread_rate),
            ("fixed_rate", fixed_rate),
            ("principal_amount", principal_amount),
            ("current_value", current_value),
            ("last_update", last_update),
        ]
        for col, value in optional_fields:
            if value is not _UNSET:
                updates.append(f"{col} = ?")
                params.append(value)

        params.extend([asset_id, uid])
        _cur_exec(cur, 
            f"""
            UPDATE assets
            SET {", ".join(updates)}
            WHERE id = ? AND user_id = ?
            """,
            params,
        )
        conn.commit()


def get_asset_by_id(asset_id: int, user_id: int | None = None):
    uid = _uid(user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        _cur_exec(cur, 
            """
            SELECT *
            FROM assets
            WHERE id = ? AND user_id = ?
            """,
            (asset_id, uid),
        )
        row = cur.fetchone()
        return dict(row) if row else None


