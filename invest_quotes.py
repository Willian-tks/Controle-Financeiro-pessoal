from __future__ import annotations

from datetime import date
import os
import sqlite3
import threading
import time
from typing import Any, Optional, Tuple

import yfinance as yf
import pandas as pd
import requests


def _call_with_timeout(fn, timeout_s: float, *args, **kwargs):
    """
    Executa fn com timeout sem travar o loop principal.
    Retorna (finished, value, error_msg).
    """
    state = {"done": False, "value": None, "error": None}

    def _target():
        try:
            state["value"] = fn(*args, **kwargs)
        except Exception as e:
            state["error"] = str(e)
        finally:
            state["done"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout_s)

    if not state["done"]:
        return False, None, f"Timeout de {timeout_s:.0f}s"
    if state["error"]:
        return True, None, state["error"]
    return True, state["value"], None


def today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def _normalize_b3(symbol: str) -> str:
    """
    Aceita 'PETR4', 'PETR4.SA', 'PETR4 SA' e devolve formato yfinance: 'PETR4.SA'
    """
    s = (symbol or "").strip().upper().replace(" ", "")
    if not s:
        return ""
    if s.endswith(".SA"):
        return s
    return f"{s}.SA"

def _to_brapi_symbol(symbol: str) -> str:
    """
    BRAPI normalmente usa o ticker B3 sem sufixo: 'PETR4' (nÃ£o 'PETR4.SA').
    """
    s = (symbol or "").strip().upper().replace(" ", "")
    if s.endswith(".SA"):
        s = s[:-3]
    return s


def _normalize_crypto(symbol: str, currency: str) -> str:
    """
    Ex: BTC + USD => BTC-USD, BTC + BRL => BTC-BRL
    """
    base = (symbol or "").strip().upper()
    cur = (currency or "USD").strip().upper()
    if not base:
        return ""
    if "-" in base:
        return base
    return f"{base}-{cur}"


def fetch_last_price_yf(symbol: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Retorna (price, px_date, src) ou (None, None, None)
    """
    try:
        sym = _normalize_b3(symbol)  # para B3; se jÃ¡ vier BTC-USD etc, isso ainda funciona se vocÃª nÃ£o chamar aqui
        t = yf.Ticker(sym)

        hist = t.history(period="5d")
        if hist is None or getattr(hist, "empty", True):
            return None, None, None

        # pega o Ãºltimo fechamento vÃ¡lido
        last_close = hist["Close"].dropna()
        if last_close.empty:
            return None, None, None

        px = float(last_close.iloc[-1])
        px_date = str(last_close.index[-1].date())
        return px, px_date, "yahoo"
    except Exception:
        return None, None, None
    
def _get_brapi_token() -> Optional[str]:
    # 1) tenta env
    token = os.getenv("BRAPI_TOKEN")
    if token:
        return token.strip()

    # 2) tenta streamlit secrets (sem quebrar se streamlit nÃ£o existir aqui)
    try:
        import streamlit as st  # import local
        token = st.secrets.get("BRAPI_TOKEN")
        if token:
            return str(token).strip()
    except Exception:
        pass

    return None


def fetch_last_price_brapi(symbol: str) -> Tuple[Optional[float], Optional[str], Optional[str], Optional[str]]:
    """
    Retorna (price, px_date, src, err)
    """
    token = _get_brapi_token()
    if not token:
        return None, None, None, "BRAPI_TOKEN nÃ£o configurado (env ou secrets.toml)."

    sym = _to_brapi_symbol(symbol)
    if not sym:
        return None, None, None, "SÃ­mbolo vazio."

    url = f"https://brapi.dev/api/quote/{sym}"
    params = {"token": token}
    headers = {"User-Agent": "finance_app/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=6)
        if r.status_code != 200:
            return None, None, None, f"BRAPI HTTP {r.status_code}: {r.text[:200]}"

        data = r.json()

        results = data.get("results") or []
        if not results:
            # BRAPI pode vir com "message" e "error"
            msg = data.get("message") or data.get("error") or "Sem results."
            return None, None, None, f"BRAPI: {msg}"

        row = results[0]

        price = row.get("regularMarketPrice")
        if price is None:
            return None, None, None, "BRAPI: sem regularMarketPrice."

        # BRAPI nem sempre manda data bonitinha. Se nÃ£o vier, usamos hoje.
        px_date = row.get("regularMarketTime")
        if px_date:
            # se vier epoch seconds, converte; se vier string, deixa
            try:
                import datetime as _dt
                px_date = _dt.datetime.fromtimestamp(int(px_date)).date().isoformat()
            except Exception:
                px_date = today_str()
        else:
            px_date = today_str()

        return float(price), str(px_date), "brapi", None

    except Exception as e:
        return None, None, None, f"BRAPI erro: {e}"


def fetch_last_price(symbol: str, asset_class: str = "", currency: str = "BRL"):
    """
    Estratégia:
    - Para ativos BR (ações/FIIs), aceita ticker com ou sem ".SA"
    - Tenta Yahoo primeiro e, se falhar em ativo BR, tenta BRAPI
    Retorna (price, px_date, src, err)
    """
    cls = (asset_class or "").strip().lower()
    cur = (currency or "BRL").strip().upper()
    sym = (symbol or "").strip().upper().replace(" ", "")

    # Heurística para identificar ativo BR mesmo que classe venha fora do padrão.
    is_b3_by_class = ("acoes" in cls) or ("ações" in cls) or ("fii" in cls) or ("b3" in cls) or ("_br" in cls)
    is_b3_like_symbol = sym.endswith(".SA") or (
        sym.isalnum()
        and any(ch.isdigit() for ch in sym)
        and "." not in sym
        and "-" not in sym
    )
    is_b3 = is_b3_by_class or (cur == "BRL" and is_b3_like_symbol)

    # 1) Para BR, prioriza BRAPI (mais estável para B3 e sem depender de ".SA")
    if is_b3:
        px, px_date, src, err = fetch_last_price_brapi(sym)
        if px is not None:
            return px, px_date, src, None

        # fallback para Yahoo caso BRAPI não retorne
        px, px_date, src = fetch_last_price_yf(_normalize_b3(sym))
        if px is not None:
            return px, px_date, src, None

        px, px_date, src = fetch_last_price_yf(sym)
        if px is not None:
            return px, px_date, src, None

        return None, None, None, err or "Sem cotação para ativo BR (BRAPI/Yahoo)."
    else:
        # 2) Não-BR: Yahoo
        px, px_date, src = fetch_last_price_yf(sym)
        if px is not None:
            return px, px_date, src, None

    return None, None, None, "Yahoo não retornou dados agora."


def update_all_prices(assets: list[dict] | None) -> list[dict]:
    """
    assets: lista de dicts com pelo menos: id, symbol, asset_class, currency
    Retorna um relatÃ³rio [{asset_id, symbol, ok, price, px_date, src, error}]
    """
    report: list[dict] = []
    timeout_s = 25.0

    for a in (assets or []):
        # garante dict (sqlite3.Row nÃ£o tem .get)
        if isinstance(a, sqlite3.Row):
            a = dict(a)

        sym = (a.get("symbol") or "").strip()
        cls = (a.get("asset_class") or "").strip()
        cur = (a.get("currency") or "BRL").strip()

        started = time.monotonic()
        finished, payload, timeout_err = _call_with_timeout(fetch_last_price, timeout_s, sym, cls, cur)
        elapsed_s = round(time.monotonic() - started, 2)

        if not finished:
            report.append({
                "asset_id": a.get("id"),
                "symbol": sym,
                "ok": False,
                "price": None,
                "px_date": None,
                "src": None,
                "elapsed_s": elapsed_s,
                "error": f"{timeout_err} ao consultar {sym}"
            })
            continue

        if payload is None:
            report.append({
                "asset_id": a.get("id"),
                "symbol": sym,
                "ok": False,
                "price": None,
                "px_date": None,
                "src": None,
                "elapsed_s": elapsed_s,
                "error": timeout_err or f"Falha interna ao consultar {sym}"
            })
            continue

        # CompatÃ­vel com fetch_last_price retornando 3 ou 4 valores
        try:
            price, px_date, src, err = payload
        except ValueError:
            price, px_date, src = payload
            err = None

        if price is None:
            report.append({
                "asset_id": a.get("id"),
                "symbol": sym,
                "ok": False,
                "price": None,
                "px_date": None,
                "src": None,
                "elapsed_s": elapsed_s,
                "error": err or "Sem cotaÃ§Ã£o (fonte nÃ£o retornou dados)"
            })
        else:
            report.append({
                "asset_id": a.get("id"),
                "symbol": sym,
                "ok": True,
                "price": float(price),
                "px_date": px_date,
                "src": src,
                "elapsed_s": elapsed_s,
                "error": None
            })

    return report
def fetch_last_price_yf(symbol: str):
    """
    Retorna (price, px_date, src) ou (None, None, None) se nÃ£o conseguir.
    """
    try:
        if not symbol or not str(symbol).strip():
            return None, None, None

        symbol = str(symbol).strip().upper()

        t = yf.Ticker(symbol)

        # use auto_adjust=False pra evitar mudanÃ§as de colunas
        hist = t.history(period="5d", interval="1d", auto_adjust=False, timeout=6)

        if hist is None or hist.empty:
            return None, None, None

        # pega Ãºltimo fechamento vÃ¡lido
        close = hist["Close"].dropna()
        if close.empty:
            return None, None, None

        last_price = float(close.iloc[-1])
        last_date = close.index[-1].date() if hasattr(close.index[-1], "date") else None

        return last_price, last_date, "yfinance"

    except (TypeError, KeyError, IndexError, ValueError):
        # aqui entra exatamente o erro que vocÃª estÃ¡ vendo dentro do yfinance
        return None, None, None

    except Exception:
        # se quiser logar depois, dÃ¡ pra printar, mas nÃ£o derruba o app
        return None, None, None

# invest_quotes.py

def normalize_symbol(asset) -> str | None:
    sym = (asset["symbol"] if asset and "symbol" in asset.keys() else None)
    cls = (asset["asset_class"] if asset and "asset_class" in asset.keys() else None)

    sym = (sym or "").strip().upper()
    cls = (cls or "").strip()

    if not sym:
        return None

    # ajuste para aÃ§Ãµes BR / FIIs (se vocÃª usa esse padrÃ£o)
    if cls in ("AÃ§Ãµes BR", "FIIs", "FII", "STOCK_FII"):
        if not sym.endswith(".SA"):
            sym = sym + ".SA"

    # cripto (exemplo: BTC vira BTC-USD)
    if cls in ("CRYPTO", "Cripto"):
        if "-" not in sym:
            sym = sym + "-USD"

    return sym
