import datetime as dt
import yfinance as yf

def _normalize_b3(symbol: str) -> str:
    s = (symbol or "").strip().upper()
    # Se já vier com .SA, mantém
    if s.endswith(".SA"):
        return s
    # Para B3 (ações/FIIs), yfinance usa .SA
    return f"{s}.SA"

def _normalize_crypto(symbol: str, currency: str) -> str:
    # Ex: BTC, ETH
    base = (symbol or "").strip().upper()
    cur = (currency or "USD").strip().upper()

    # yfinance: BTC-USD, BTC-BRL, ETH-USD...
    if "-" in base:
        return base  # já veio pronto
    return f"{base}-{cur}"

def fetch_last_price(symbol: str, asset_class: str, currency: str = "BRL") -> float | None:
    """
    Retorna a última cotação disponível (float) ou None se não achar.
    """
    asset_class = (asset_class or "").strip().upper()

    if asset_class in ("STOCK_FII", "STOCK", "FII"):
        ticker = _normalize_b3(symbol)
    elif asset_class in ("CRYPTO",):
        ticker = _normalize_crypto(symbol, currency if currency else "USD")
    else:
        # FIXED_INCOME e outros: sem cotação automática por enquanto
        return None

    try:
        t = yf.Ticker(ticker)

        # tenta pegar o "último" do histórico de 5 dias
        hist = t.history(period="5d", interval="1d")
        if hist is None or hist.empty:
            return None

        last_close = float(hist["Close"].dropna().iloc[-1])
        if last_close <= 0:
            return None

        return last_close
    except Exception:
        return None

def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")

def update_all_prices(assets: list[dict]) -> list[dict]:
    """
    assets: lista de dicts com pelo menos: id, symbol, asset_class, currency
    Retorna um relatório [{symbol, ok, price, error}]
    """
    date = today_str()
    report = []

    for a in assets:
        sym = a.get("symbol")
        cls = a.get("asset_class")
        cur = a.get("currency", "BRL")

        price = fetch_last_price(sym, cls, cur)
        if price is None:
            report.append({"symbol": sym, "ok": False, "price": None, "error": "Sem preço/ativo não suportado"})
        else:
            report.append({"symbol": sym, "ok": True, "price": price, "error": None})

    return report