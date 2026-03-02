from __future__ import annotations

import os
from datetime import date as _date
from datetime import datetime
from typing import Any

import requests

from db import get_conn

SUPPORTED_INDEX_NAMES = ("CDI", "SELIC", "IPCA")


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


def fetch_bcb_series(index_name: str, date_from: str, date_to: str, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    idx = norm_index_name(index_name)
    if idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")

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

    resp = requests.get(url, params=params, headers=headers, timeout=float(timeout_s))
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


def list_index_rates(
    index_name: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    idx = norm_index_name(index_name) if index_name else None
    if idx and idx not in SUPPORTED_INDEX_NAMES:
        raise ValueError(f"Índice não suportado: {index_name}")

    d_from = _parse_iso_date(date_from) if date_from else None
    d_to = _parse_iso_date(date_to) if date_to else None
    lim = max(1, min(int(limit or 2000), 10000))

    sql = """
        SELECT id, index_name, ref_date, value, source, created_at, updated_at, user_id
        FROM index_rates
        WHERE 1=1
    """
    params: list[Any] = []
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
        rows = conn.execute(sql, params).fetchall()
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
    uid = int(user_id) if user_id is not None else None
    inserted = 0
    updated = 0
    unchanged = 0

    with get_conn() as conn:
        for ref_date, value, src in normalized:
            existing = conn.execute(
                "SELECT value, source FROM index_rates WHERE index_name = ? AND ref_date = ?",
                (idx, ref_date),
            ).fetchone()

            if existing is None:
                conn.execute(
                    """
                    INSERT INTO index_rates(index_name, ref_date, value, source, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (idx, ref_date, value, src, uid),
                )
                inserted += 1
                continue

            old_value = float(existing["value"])
            old_source = (str(existing["source"]).strip() if existing["source"] is not None else None)
            if abs(old_value - value) < 1e-12 and old_source == src:
                unchanged += 1
                continue

            conn.execute(
                """
                UPDATE index_rates
                SET value = ?, source = ?, updated_at = CURRENT_TIMESTAMP
                WHERE index_name = ? AND ref_date = ?
                """,
                (value, src, idx, ref_date),
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
        points = fetch_bcb_series(idx, d_from, d_to, timeout_s=timeout_s)
        res = bulk_upsert_index_rates(
            index_name=idx,
            points=points,
            source="BCB",
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
