import argparse
from datetime import datetime, timedelta
from typing import Any

import certifi
import requests

import invest_quotes
import invest_repo
from tenant import clear_tenant_context, set_current_user_id, set_current_workspace_id


SUPPORTED_CLASSES = {
    "acoes br",
    "ações br",
    "fiis",
    "fii",
    "stocks us",
    "stock us",
    "bdrs",
    "cripto",
    "crypto",
}


def _parse_date(value: str | None, fallback: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()


def _history_symbol(asset: dict[str, Any]) -> str | None:
    symbol = str(asset.get("symbol") or "").strip().upper()
    asset_class = str(asset.get("asset_class") or "").strip().lower()
    currency = str(asset.get("currency") or "BRL").strip().upper()
    if not symbol:
        return None
    if asset_class in {"acoes br", "ações br", "fiis", "fii", "bdrs"}:
        return invest_quotes._normalize_b3(symbol)
    if asset_class in {"crypto", "cripto"}:
        return invest_quotes._normalize_crypto(symbol, currency or "USD")
    if asset_class in {"stocks us", "stock us"}:
        return symbol
    return None


def _fetch_yahoo_history(symbol: str, date_from: str, date_to: str, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    start_ts = int(datetime.strptime(date_from, "%Y-%m-%d").timestamp())
    end_ts = int(datetime.strptime(date_to, "%Y-%m-%d").timestamp()) + 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "includeAdjustedClose": "true",
        "events": "div,splits",
    }
    headers = {"User-Agent": "controle-financeiro/1.0"}
    resp = requests.get(url, params=params, headers=headers, timeout=float(timeout_s), verify=certifi.where())
    if resp.status_code != 200:
        raise RuntimeError(f"Yahoo HTTP {resp.status_code} para {symbol}")
    payload = resp.json() or {}
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        raise RuntimeError(f"Yahoo erro para {symbol}: {error}")
    result = (chart.get("result") or [None])[0] or {}
    timestamps = list(result.get("timestamp") or [])
    quote = (((result.get("indicators") or {}).get("quote")) or [None])[0] or {}
    closes = list(quote.get("close") or [])

    points = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        ref_date = datetime.utcfromtimestamp(int(ts)).date().isoformat()
        points.append({"date": ref_date, "price": float(close)})
    return points


def run_backfill(
    *,
    workspace_id: int,
    user_id: int,
    date_from: str,
    date_to: str,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    set_current_workspace_id(int(workspace_id))
    set_current_user_id(int(user_id))
    assets = [dict(row) for row in (invest_repo.list_assets(user_id=int(user_id)) or [])]
    report: list[dict[str, Any]] = []
    inserted_total = 0
    processed_total = 0

    try:
        for asset in assets:
            asset_class = str(asset.get("asset_class") or "").strip().lower()
            if asset_class not in SUPPORTED_CLASSES:
                continue
            history_symbol = _history_symbol(asset)
            if not history_symbol:
                report.append({"symbol": asset.get("symbol"), "ok": False, "reason": "unsupported_symbol"})
                continue

            try:
                points = _fetch_yahoo_history(history_symbol, date_from, date_to, timeout_s=timeout_s)
                saved = 0
                for point in points:
                    invest_repo.upsert_price(
                        asset_id=int(asset["id"]),
                        date=str(point["date"]),
                        price=float(point["price"]),
                        source="history_backfill",
                        user_id=int(user_id),
                    )
                    saved += 1
                inserted_total += saved
                processed_total += 1
                report.append({"symbol": asset.get("symbol"), "ok": True, "saved": saved, "history_symbol": history_symbol})
            except Exception as exc:
                report.append({"symbol": asset.get("symbol"), "ok": False, "reason": str(exc), "history_symbol": history_symbol})
    finally:
        clear_tenant_context()

    return {
        "ok": True,
        "workspace_id": int(workspace_id),
        "user_id": int(user_id),
        "date_from": date_from,
        "date_to": date_to,
        "processed_assets": processed_total,
        "saved_points": inserted_total,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill local do histórico de preços dos investimentos.")
    parser.add_argument("--workspace-id", type=int, default=1)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--date-from", default=(datetime.today().date() - timedelta(days=365)).isoformat())
    parser.add_argument("--date-to", default=datetime.today().date().isoformat())
    parser.add_argument("--timeout-s", type=float, default=20.0)
    args = parser.parse_args(argv)

    result = run_backfill(
        workspace_id=int(args.workspace_id),
        user_id=int(args.user_id),
        date_from=_parse_date(args.date_from, (datetime.today().date() - timedelta(days=365)).isoformat()),
        date_to=_parse_date(args.date_to, datetime.today().date().isoformat()),
        timeout_s=float(args.timeout_s),
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
