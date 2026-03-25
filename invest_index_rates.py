from __future__ import annotations

import os
import re
from datetime import date as _date
from datetime import datetime
from contextvars import ContextVar
from typing import Any

import requests
import certifi

from db import get_conn
from tenant import get_current_user_id, get_current_workspace_id

SUPPORTED_INDEX_NAMES = ("CDI", "SELIC", "IPCA", "IBOV", "IFIX", "SP500", "GLOBAL", "CRYPTO")
_USE_WORKSPACE_SCOPE: ContextVar[bool] = ContextVar("invest_index_rates_use_workspace_scope", default=False)


def _wid(user_id: int | None = None) -> int:
    wid = get_current_workspace_id(required=False)
    if wid is not None:
        _USE_WORKSPACE_SCOPE.set(True)
        return int(wid)

    uid = int(user_id) if user_id is not None else int(get_current_user_id())
    conn = get_conn()
    try:
        row = conn.execute(
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


def norm_index_name(value: str | None) -> str:
    raw = str(value or "").strip().upper()
    raw = (
        raw.replace("Ã", "A")
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    if raw in {"SELIC", "SELICA", "SELIC AA"}:
        return "SELIC"
    if raw in {"CDI", "DI"}:
        return "CDI"
    if raw in {"IPCA"}:
        return "IPCA"
    if raw in {"IBOV", "IBOVESPA", "IBOV INDEX"}:
        return "IBOV"
    if raw in {"IFIX", "IFIX INDEX"}:
        return "IFIX"
    if raw in {"SP500", "S&P500", "S&P 500", "SPX", "GSPC"}:
        return "SP500"
    if raw in {"GLOBAL", "WORLD", "ACWI", "INTERNACIONAL", "INDICE INTERNACIONAL"}:
        return "GLOBAL"
    if raw in {"CRYPTO", "CRYPTO_BENCH", "CRYPTO INDEX", "INDICE CRIPTO"}:
        return "CRYPTO"
    return raw


def _parse_iso_date(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Data obrigatória no formato YYYY-MM-DD.")
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Data inválida: '{raw}'. Use YYYY-MM-DD.") from exc


def _iso_to_bcb_date(value: str) -> str:
    dt = datetime.strptime(value, "%Y-%m-%d").date()
    return dt.strftime("%d/%m/%Y")


def _bcb_to_iso_date(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Data vazia retornada pela fonte.")
    return datetime.strptime(raw, "%d/%m/%Y").date().isoformat()


def _to_float(value: Any) -> float:
    txt = str(value or "").strip().replace(",", ".")
    if not txt:
        raise ValueError("Valor vazio.")
    return float(txt)


def _series_code(index_name: str) -> int:
    idx = norm_index_name(index_name)
    defaults = {
        "CDI": "12",
        "SELIC": "11",
        "IPCA": "433",
    }
    raw = os.getenv(f"BCB_SERIES_{idx}", defaults.get(idx, "")).strip()
    if not raw:
        raise ValueError(f"Código da série não configurado para {idx}.")
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Código inválido para {idx}: {raw}") from exc


def _index_source(index_name: str) -> str:
    idx = norm_index_name(index_name)
    if idx in {"CDI", "SELIC", "IPCA"}:
        return "BCB"
    if idx in {"IBOV", "IFIX", "SP500", "GLOBAL", "CRYPTO"}:
        return "YAHOO"
    raise ValueError(f"Índice não suportado: {index_name}")


def _market_symbol(index_name: str) -> str:
    idx = norm_index_name(index_name)
    defaults = {
        "IBOV": "^BVSP",
        "IFIX": "^IFIX",
        "SP500": "^GSPC",
        "GLOBAL": "ACWI",
        "CRYPTO": "BTC-USD",
    }
    raw = str(os.getenv(f"MARKET_INDEX_SYMBOL_{idx}", defaults.get(idx, "")) or "").strip()
    if not raw:
        raise ValueError(f"Ticker de mercado não configurado para {idx}.")
    return raw


def fetch_bcb_series(index_name: str, date_from: str, date_to: str, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    idx = norm_index_name(index_name)
    if idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")
    if _index_source(idx) != "BCB":
        raise ValueError(f"Índice {idx} não usa fonte BCB.")

    d_from = _parse_iso_date(date_from)
    d_to = _parse_iso_date(date_to)
    if d_from > d_to:
        raise ValueError("date_from não pode ser maior que date_to.")

    code = _series_code(idx)
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    params = {
        "formato": "json",
        "dataInicial": _iso_to_bcb_date(d_from),
        "dataFinal": _iso_to_bcb_date(d_to),
    }
    headers = {"User-Agent": "controle-financeiro/1.0"}

    resp = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=float(timeout_s),
        verify=certifi.where(),
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Falha ao consultar BCB ({idx}): HTTP {resp.status_code}")

    payload = resp.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"Resposta inesperada do BCB para {idx}.")

    points: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        try:
            ref_date = _bcb_to_iso_date(str(row.get("data") or ""))
            value = _to_float(row.get("valor"))
        except Exception:
            continue
        points.append(
            {
                "index_name": idx,
                "ref_date": ref_date,
                "value": value,
                "source": "BCB",
            }
        )

    points.sort(key=lambda x: x["ref_date"])
    return points


def fetch_yahoo_series(index_name: str, date_from: str, date_to: str, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    idx = norm_index_name(index_name)
    if idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")
    if _index_source(idx) != "YAHOO":
        raise ValueError(f"Índice {idx} não usa fonte Yahoo.")

    d_from = _parse_iso_date(date_from)
    d_to = _parse_iso_date(date_to)
    if d_from > d_to:
        raise ValueError("date_from não pode ser maior que date_to.")

    symbol = _market_symbol(idx)
    start_ts = int(datetime.strptime(d_from, "%Y-%m-%d").timestamp())
    # Yahoo chart uses period2 as exclusive end; add one day to include d_to.
    end_dt = datetime.strptime(d_to, "%Y-%m-%d")
    end_ts = int(end_dt.timestamp()) + 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "includeAdjustedClose": "true",
        "events": "div,splits",
    }
    headers = {"User-Agent": "controle-financeiro/1.0"}
    resp = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=float(timeout_s),
        verify=certifi.where(),
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Falha ao consultar Yahoo ({idx}): HTTP {resp.status_code}")

    payload = resp.json() or {}
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        raise RuntimeError(f"Yahoo retornou erro para {idx}: {error}")
    result = (chart.get("result") or [None])[0] or {}
    timestamps = list(result.get("timestamp") or [])
    quote = (((result.get("indicators") or {}).get("quote")) or [None])[0] or {}
    closes = list(quote.get("close") or [])

    points: list[dict[str, Any]] = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        try:
            ref_date = datetime.utcfromtimestamp(int(ts)).date().isoformat()
            value = float(close)
        except Exception:
            continue
        points.append(
            {
                "index_name": idx,
                "ref_date": ref_date,
                "value": value,
                "source": "YAHOO",
            }
        )
    points.sort(key=lambda x: x["ref_date"])
    return points


def fetch_index_series(index_name: str, date_from: str, date_to: str, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    source = _index_source(index_name)
    if source == "BCB":
        return fetch_bcb_series(index_name, date_from, date_to, timeout_s=timeout_s)
    if source == "YAHOO":
        return fetch_yahoo_series(index_name, date_from, date_to, timeout_s=timeout_s)
    raise ValueError(f"Fonte não suportada para índice: {index_name}")


def list_index_rates(
    index_name: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 2000,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    idx = norm_index_name(index_name) if index_name else None
    if idx and idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")

    d_from = _parse_iso_date(date_from) if date_from else None
    d_to = _parse_iso_date(date_to) if date_to else None
    lim = max(1, min(int(limit or 2000), 10000))
    wid = _wid(user_id)

    sql = """
        SELECT id, index_name, ref_date, value, source, created_at, updated_at, user_id
        FROM index_rates
        WHERE user_id = ?
    """
    params: list[Any] = [wid]
    if idx:
        sql += " AND index_name = ?"
        params.append(idx)
    if d_from:
        sql += " AND ref_date >= ?"
        params.append(d_from)
    if d_to:
        sql += " AND ref_date <= ?"
        params.append(d_to)
    sql += " ORDER BY ref_date DESC, index_name ASC LIMIT ?"
    params.append(lim)

    with get_conn() as conn:
        rows = _exec(conn, sql, params).fetchall()
    return [dict(r) for r in rows]


def bulk_upsert_index_rates(
    index_name: str,
    points: list[dict[str, Any]],
    source: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    idx = norm_index_name(index_name)
    if idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")

    normalized: list[tuple[str, float, str | None]] = []
    for p in points or []:
        ref_date = _parse_iso_date(str((p or {}).get("ref_date") or ""))
        value = float((p or {}).get("value"))
        src = (str((p or {}).get("source") or source or "").strip() or None)
        normalized.append((ref_date, value, src))

    normalized.sort(key=lambda item: item[0])
    wid = _wid(user_id)
    inserted = 0
    updated = 0
    unchanged = 0

    with get_conn() as conn:
        for ref_date, value, src in normalized:
            existing = _exec(conn, 
                "SELECT value, source FROM index_rates WHERE user_id = ? AND index_name = ? AND ref_date = ?",
                (wid, idx, ref_date),
            ).fetchone()

            if existing is None:
                _exec(conn, 
                    """
                    INSERT INTO index_rates(index_name, ref_date, value, source, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (idx, ref_date, value, src, wid),
                )
                inserted += 1
                continue

            old_value = float(existing["value"])
            old_source = (str(existing["source"]).strip() if existing["source"] is not None else None)
            if old_source and old_source.upper().startswith("MANUAL") and (not src or not src.upper().startswith("MANUAL")):
                unchanged += 1
                continue
            if abs(old_value - value) < 1e-12 and old_source == src:
                unchanged += 1
                continue

            _exec(conn, 
                """
                UPDATE index_rates
                SET value = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND index_name = ? AND ref_date = ?
                """,
                (value, src, wid, idx, ref_date),
            )
            updated += 1

    return {
        "index_name": idx,
        "total": len(normalized),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
    }


def sync_from_bcb(
    index_names: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    timeout_s: float = 20.0,
    user_id: int | None = None,
) -> dict[str, Any]:
    names_raw = index_names or list(SUPPORTED_INDEX_NAMES)
    names: list[str] = []
    for name in names_raw:
        idx = norm_index_name(name)
        if idx not in SUPPORTED_INDEX_NAMES:
            raise ValueError(f"Índice não suportado: {name}")
        if idx not in names:
            names.append(idx)

    d_to = _parse_iso_date(date_to) if date_to else _date.today().isoformat()
    d_from = _parse_iso_date(date_from) if date_from else f"{_date.today().year}-01-01"
    if d_from > d_to:
        raise ValueError("date_from não pode ser maior que date_to.")

    out: dict[str, Any] = {
        "date_from": d_from,
        "date_to": d_to,
        "indexes": {},
    }
    total_inserted = 0
    total_updated = 0
    total_unchanged = 0

    for idx in names:
        points = fetch_index_series(idx, d_from, d_to, timeout_s=timeout_s)
        res = bulk_upsert_index_rates(
            index_name=idx,
            points=points,
            source=_index_source(idx),
            user_id=user_id,
        )
        out["indexes"][idx] = res
        total_inserted += int(res["inserted"])
        total_updated += int(res["updated"])
        total_unchanged += int(res["unchanged"])

    out["totals"] = {
        "inserted": total_inserted,
        "updated": total_updated,
        "unchanged": total_unchanged,
    }
    return out
