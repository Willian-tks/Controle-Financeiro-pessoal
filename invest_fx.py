"""Public USD/BRL closing references; acquisition rates remain on trades."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
from urllib.parse import urlencode, quote

import requests
from db import get_conn

SOURCE = "BCB PTAX venda"
URL = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
       "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)")


def today():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def create_schema(conn):
    # Shared public market data only: no balances, operations or tenant identifiers.
    conn.execute("""CREATE TABLE IF NOT EXISTS investment_fx_rates (
        rate_date TEXT PRIMARY KEY,
        rate DOUBLE PRECISION NOT NULL CHECK (rate > 0),
        source TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )""")


def load_rates():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT rate_date, rate, source FROM investment_fx_rates ORDER BY rate_date"
        ).fetchall()]


def fetch_ptax(start: date, end: date):
    if start > end or (end - start).days > 366:
        raise ValueError("Consulte intervalos de até 366 dias.")
    response = requests.get(URL, params=urlencode({
        "@moeda": "'USD'", "@dataInicial": start.strftime("'%m-%d-%Y'"),
        "@dataFinalCotacao": end.strftime("'%m-%d-%Y'"), "$format": "json",
        "$filter": "tipoBoletim eq 'Fechamento'", "$top": 1000,
        "$orderby": "dataHoraCotacao asc",
    }, quote_via=quote), timeout=15)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
        raise ValueError("Resposta PTAX inválida.")
    rows = {}
    for row in payload["value"]:
        if row.get("tipoBoletim") != "Fechamento":
            continue
        day = date.fromisoformat(str(row["dataHoraCotacao"])[:10])
        rate = float(row["cotacaoVenda"])
        if not start <= day <= end or not math.isfinite(rate) or rate <= 0:
            raise ValueError("Referência PTAX inválida.")
        rows[day.isoformat()] = rate
    return rows


def refresh_rates(start=None, end=None):
    end = min(date.fromisoformat(end) if end else today(), today())
    start = date.fromisoformat(start) if start else end - timedelta(days=30)
    rows = fetch_ptax(start, end)
    if not rows:
        raise ValueError("BCB não retornou fechamento PTAX no período.")
    with get_conn() as conn:
        for day, rate in rows.items():
            conn.execute("""INSERT INTO investment_fx_rates(rate_date, rate, source, fetched_at)
                VALUES (?, ?, ?, ?) ON CONFLICT(rate_date) DO UPDATE SET
                rate = excluded.rate, source = excluded.source, fetched_at = excluded.fetched_at""",
                (day, rate, SOURCE, datetime.now(ZoneInfo("UTC")).isoformat()))
    return {"ok": True, "saved": len(rows), "date": max(rows), "source": SOURCE}


def refresh_for_assets(assets):
    if not any(str(dict(a).get("currency") or "").strip().upper() == "USD" for a in assets):
        return {"ok": True, "skipped": True}
    # A published closing reference is stable for the rest of its day.
    rates = load_rates()
    if rates and rates[-1]["rate_date"] == today().isoformat():
        return {"ok": True, "cached": True, "date": rates[-1]["rate_date"], "source": SOURCE}
    try:
        return refresh_rates()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return {"ok": False, "message": "PTAX indisponível; referências anteriores preservadas."}


def reference_at(rates, as_of):
    cutoff = str(as_of)[:10]
    return next((r for r in reversed(rates) if str(r["rate_date"]) <= cutoff), None)


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Carrega referências PTAX, sem alterar operações.")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD (máximo 366 dias)")
    args = parser.parse_args()
    print(json.dumps(refresh_rates(args.start, args.end), ensure_ascii=False))
