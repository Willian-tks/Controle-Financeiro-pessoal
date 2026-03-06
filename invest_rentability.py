from __future__ import annotations

import math
from datetime import date as _date
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
import re
from contextvars import ContextVar
from typing import Any

from db import get_conn
from tenant import get_current_user_id, get_current_workspace_id

getcontext().prec = 40

_RATE_Q = Decimal("0.00000001")
_INTERMEDIATE_Q = Decimal("0.000001")
_CURRENT_Q = Decimal("0.000001")
_BUSINESS_DAYS_YEAR = Decimal("252")
_FIXED_INCOME_CLASSES = {"renda_fixa", "tesouro_direto", "coe", "fundos"}
_USE_WORKSPACE_SCOPE: ContextVar[bool] = ContextVar("invest_rentability_use_workspace_scope", default=False)


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


def _norm_text(value: str | None) -> str:
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


def _is_fixed_income(asset_class: str | None) -> bool:
    return _norm_text(asset_class) in _FIXED_INCOME_CLASSES


def _parse_date(value: str | None, field_name: str) -> _date:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} obrigatório (YYYY-MM-DD).")
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} inválido: '{raw}'. Use YYYY-MM-DD.") from exc


def _optional_date(value: str | None) -> _date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_business_day(d: _date) -> bool:
    return d.weekday() < 5


def _iter_days(date_from: _date, date_to: _date):
    cur = date_from
    while cur <= date_to:
        yield cur
        cur += timedelta(days=1)


def _is_month_end(d: _date) -> bool:
    return (d + timedelta(days=1)).month != d.month


def _to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    if value is None:
        return default
    txt = str(value).strip()
    if txt == "":
        return default
    return Decimal(txt.replace(",", "."))


def _q_rate(value: Decimal) -> Decimal:
    return value.quantize(_RATE_Q, rounding=ROUND_HALF_UP)


def _q_intermediate(value: Decimal) -> Decimal:
    return value.quantize(_INTERMEDIATE_Q, rounding=ROUND_HALF_UP)


def _annual_pct_to_daily_rate(annual_pct: Decimal) -> Decimal:
    annual_decimal = Decimal(annual_pct) / Decimal("100")
    if annual_decimal <= Decimal("-1"):
        return Decimal("-1")
    # base 252 dias úteis (decisão de negócio)
    daily = Decimal(str(math.pow(float(Decimal("1") + annual_decimal), float(Decimal("1") / _BUSINESS_DAYS_YEAR)) - 1.0))
    return _q_rate(daily)


def _daily_rate_from_index_value(index_value_pct: Decimal) -> Decimal:
    # Heurística:
    # - valor > 1% tende a ser anual (ex.: SELIC anualizada)
    # - valor <= 1% tende a ser taxa diária (ex.: CDI diário)
    if abs(index_value_pct) > Decimal("1"):
        return _annual_pct_to_daily_rate(index_value_pct)
    return _q_rate(index_value_pct / Decimal("100"))


def _factor_from_rate(rate_decimal: Decimal) -> Decimal:
    return _q_intermediate(Decimal("1") + rate_decimal)


def _resolve_base_date(conn, asset_row: dict[str, Any]) -> _date:
    trade_row = _exec(conn, 
        """
        SELECT MIN(date) AS min_buy_date
        FROM trades
        WHERE asset_id = ?
          AND COALESCE(user_id, 0) = COALESCE(?, 0)
          AND UPPER(COALESCE(side, '')) = 'BUY'
        """,
        (
            int(asset_row["id"]),
            asset_row.get("workspace_id", asset_row.get("user_id")),
        ),
    ).fetchone()
    buy_date = _optional_date((trade_row["min_buy_date"] if trade_row else None))
    if buy_date:
        return buy_date
    created_date = _optional_date(asset_row.get("created_at"))
    return created_date or _date.today()


def _load_daily_index_map(conn, index_name: str, date_from: _date, date_to: _date) -> dict[_date, Decimal]:
    rows = _exec(conn, 
        """
        SELECT ref_date, value
        FROM index_rates
        WHERE index_name = ?
          AND ref_date >= ?
          AND ref_date <= ?
        ORDER BY ref_date
        """,
        (index_name, date_from.isoformat(), date_to.isoformat()),
    ).fetchall()
    out: dict[_date, Decimal] = {}
    for r in rows:
        d = _optional_date(r["ref_date"])
        if not d:
            continue
        out[d] = _to_decimal(r["value"], Decimal("0")) or Decimal("0")
    return out


def _load_monthly_ipca_map(conn, date_from: _date, date_to: _date) -> dict[str, Decimal]:
    fetch_from = _date(int(date_from.year), int(date_from.month), 1)
    rows = _exec(conn, 
        """
        SELECT ref_date, value
        FROM index_rates
        WHERE index_name = 'IPCA'
          AND ref_date >= ?
          AND ref_date <= ?
        ORDER BY ref_date
        """,
        (fetch_from.isoformat(), date_to.isoformat()),
    ).fetchall()
    out: dict[str, Decimal] = {}
    for r in rows:
        d = _optional_date(r["ref_date"])
        if not d:
            continue
        out[f"{d.year:04d}-{d.month:02d}"] = _q_rate((_to_decimal(r["value"], Decimal("0")) or Decimal("0")) / Decimal("100"))
    return out


def _norm_rentability_type(value: str | None) -> str:
    raw = _norm_text(value)
    mapping = {
        "prefixado": "PREFIXADO",
        "pct_cdi": "PCT_CDI",
        "pct_di": "PCT_CDI",
        "pct_selic": "PCT_SELIC",
        "cdi_spread": "CDI_SPREAD",
        "cdi_x": "CDI_SPREAD",
        "selic_spread": "SELIC_SPREAD",
        "selic_x": "SELIC_SPREAD",
        "ipca_spread": "IPCA_SPREAD",
        "ipca_x": "IPCA_SPREAD",
        "manual": "MANUAL",
    }
    return mapping.get(raw, str(value or "").strip().upper())


def _is_auto_rentability_type(value: str | None) -> bool:
    rt = _norm_rentability_type(value)
    return rt in {"PREFIXADO", "PCT_CDI", "PCT_SELIC", "CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD"}


def _norm_index_name(value: str | None) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"DI", "CDI"}:
        return "CDI"
    if raw.startswith("SELIC"):
        return "SELIC"
    if raw == "IPCA":
        return "IPCA"
    return raw


def _simulate_asset_value(conn, asset: dict[str, Any], as_of: _date) -> dict[str, Any]:
    if not _is_fixed_income(asset.get("asset_class")):
        return {"ok": True, "updated": False, "reason": "not_fixed_income"}

    rent_type = _norm_rentability_type(asset.get("rentability_type") or "MANUAL")
    if not rent_type:
        rent_type = "MANUAL"

    current_value = _to_decimal(asset.get("current_value"))
    principal_amount = _to_decimal(asset.get("principal_amount"))
    base_value = current_value if current_value is not None else principal_amount
    if base_value is None:
        return {"ok": False, "updated": False, "reason": "missing_base_value"}

    base_date = _resolve_base_date(conn, asset)
    last_update = _optional_date(asset.get("last_update")) or base_date
    start_date = last_update + timedelta(days=1)
    if start_date > as_of:
        return {"ok": True, "updated": False, "reason": "already_up_to_date", "current_value": float(base_value), "last_update": last_update.isoformat()}

    if rent_type == "MANUAL":
        if current_value is None and principal_amount is not None:
            saved = principal_amount.quantize(_CURRENT_Q, rounding=ROUND_HALF_UP)
            return {
                "ok": True,
                "updated": True,
                "reason": "manual_initialized",
                "current_value": float(saved),
                "last_update": asset.get("last_update"),
                "rentability_type": "MANUAL",
                "processed_steps": 0,
            }
        return {"ok": True, "updated": False, "reason": "manual_mode", "current_value": float(current_value or base_value), "last_update": asset.get("last_update"), "rentability_type": "MANUAL", "processed_steps": 0}

    current = Decimal(base_value)
    processed_days = 0
    effective_last_date = last_update

    if rent_type == "PREFIXADO":
        fixed_rate = _to_decimal(asset.get("fixed_rate"))
        if fixed_rate is None:
            return {"ok": False, "updated": False, "reason": "missing_fixed_rate"}
        daily_rate = _annual_pct_to_daily_rate(fixed_rate)
        factor = _factor_from_rate(daily_rate)
        for d in _iter_days(start_date, as_of):
            if not _is_business_day(d):
                continue
            current *= factor
            processed_days += 1
            effective_last_date = d

    elif rent_type in {"PCT_CDI", "PCT_SELIC"}:
        idx_name = _norm_index_name(asset.get("index_name") or ("CDI" if rent_type == "PCT_CDI" else "SELIC"))
        idx_pct = _to_decimal(asset.get("index_pct"))
        if idx_pct is None:
            return {"ok": False, "updated": False, "reason": "missing_index_pct"}
        pct_multiplier = _q_rate(idx_pct / Decimal("100"))
        spread_rate = _to_decimal(asset.get("spread_rate"), Decimal("0")) or Decimal("0")
        spread_daily_rate = _annual_pct_to_daily_rate(spread_rate) if spread_rate != 0 else Decimal("0")

        idx_map = _load_daily_index_map(conn, idx_name, start_date, as_of)
        applicable_dates = sorted([d for d in idx_map.keys() if d >= start_date and d <= as_of])
        if not applicable_dates:
            return {
                "ok": True,
                "updated": False,
                "reason": "missing_index_data",
                "current_value": float(current),
                "last_update": last_update.isoformat(),
                "rentability_type": rent_type,
                "processed_steps": 0,
            }
        for d in applicable_dates:
            base_rate = _daily_rate_from_index_value(idx_map[d])
            eff_rate = _q_rate((base_rate * pct_multiplier) + spread_daily_rate)
            current *= _factor_from_rate(eff_rate)
            processed_days += 1
            effective_last_date = d

    elif rent_type in {"CDI_SPREAD", "SELIC_SPREAD"}:
        idx_name = _norm_index_name(asset.get("index_name") or ("CDI" if rent_type == "CDI_SPREAD" else "SELIC"))
        spread_rate = _to_decimal(asset.get("spread_rate"))
        if spread_rate is None:
            return {"ok": False, "updated": False, "reason": "missing_spread_rate"}
        spread_daily_rate = _annual_pct_to_daily_rate(spread_rate)

        idx_map = _load_daily_index_map(conn, idx_name, start_date, as_of)
        applicable_dates = sorted([d for d in idx_map.keys() if d >= start_date and d <= as_of])
        if not applicable_dates:
            return {
                "ok": True,
                "updated": False,
                "reason": "missing_index_data",
                "current_value": float(current),
                "last_update": last_update.isoformat(),
                "rentability_type": rent_type,
                "processed_steps": 0,
            }
        for d in applicable_dates:
            base_rate = _daily_rate_from_index_value(idx_map[d])
            eff_rate = _q_rate(base_rate + spread_daily_rate)
            current *= _factor_from_rate(eff_rate)
            processed_days += 1
            effective_last_date = d

    elif rent_type == "IPCA_SPREAD":
        spread_rate = _to_decimal(asset.get("spread_rate"))
        if spread_rate is None:
            return {"ok": False, "updated": False, "reason": "missing_spread_rate"}
        spread_daily_rate = _annual_pct_to_daily_rate(spread_rate)
        spread_factor = _factor_from_rate(spread_daily_rate)
        ipca_map = _load_monthly_ipca_map(conn, start_date, as_of)

        for d in _iter_days(start_date, as_of):
            if _is_month_end(d):
                key = f"{d.year:04d}-{d.month:02d}"
                if key not in ipca_map:
                    break
            if _is_business_day(d):
                current *= spread_factor
                processed_days += 1
            if _is_month_end(d):
                current *= _factor_from_rate(ipca_map[f"{d.year:04d}-{d.month:02d}"])
                processed_days += 1
            effective_last_date = d

    else:
        return {"ok": False, "updated": False, "reason": f"unsupported_type:{rent_type}"}

    if effective_last_date <= last_update:
        return {
            "ok": True,
            "updated": False,
            "reason": "nothing_to_apply",
            "current_value": float(current),
            "last_update": last_update.isoformat(),
            "rentability_type": rent_type,
            "processed_steps": processed_days,
        }

    saved_current = current.quantize(_CURRENT_Q, rounding=ROUND_HALF_UP)
    return {
        "ok": True,
        "updated": True,
        "reason": "updated",
        "current_value": float(saved_current),
        "last_update": effective_last_date.isoformat(),
        "rentability_type": rent_type,
        "processed_steps": int(processed_days),
    }


def update_investment_value(asset_id: int, as_of_date: str | None = None, user_id: int | None = None) -> dict[str, Any]:
    uid = _uid(user_id)
    as_of = _parse_date(as_of_date, "as_of_date") if as_of_date else _date.today()

    with get_conn() as conn:
        row = _exec(conn, 
            """
            SELECT
                id, user_id, created_at, asset_class, rentability_type, index_name,
                index_pct, spread_rate, fixed_rate, principal_amount, current_value, last_update
            FROM assets
            WHERE id = ? AND user_id = ?
            """,
            (int(asset_id), uid),
        ).fetchone()
        if not row:
            return {"ok": False, "asset_id": int(asset_id), "updated": False, "reason": "asset_not_found"}

        asset = dict(row)
        sim = _simulate_asset_value(conn, asset, as_of)
        if not sim.get("ok", False):
            return {"ok": False, "asset_id": int(asset_id), "updated": False, "reason": sim.get("reason", "calc_error")}
        if not sim.get("updated", False):
            out = {
                "ok": True,
                "asset_id": int(asset_id),
                "updated": False,
                "reason": sim.get("reason", "no_change"),
            }
            if sim.get("last_update") is not None:
                out["last_update"] = sim.get("last_update")
            return out

        _exec(conn, 
            """
            UPDATE assets
            SET current_value = ?, last_update = ?
            WHERE id = ? AND user_id = ?
            """,
            (float(sim["current_value"]), sim.get("last_update"), int(asset_id), uid),
        )
        return {
            "ok": True,
            "asset_id": int(asset_id),
            "updated": True,
            "rentability_type": sim.get("rentability_type"),
            "processed_steps": int(sim.get("processed_steps", 0)),
            "current_value": float(sim["current_value"]),
            "last_update": sim.get("last_update"),
        }


def update_fixed_income_assets(
    as_of_date: str | None = None,
    user_id: int | None = None,
    only_auto: bool = True,
    reset_from_principal: bool = False,
    asset_ids: list[int] | None = None,
    exclude_asset_ids: list[int] | None = None,
) -> dict[str, Any]:
    uid = _uid(user_id)
    as_of = _parse_date(as_of_date, "as_of_date") if as_of_date else _date.today()

    with get_conn() as conn:
        rows = _exec(conn, 
            """
            SELECT
                id, user_id, created_at, asset_class, rentability_type, principal_amount
            FROM assets
            WHERE user_id = ?
              AND (
                LOWER(REPLACE(COALESCE(asset_class, ''), '_', ' ')) IN ('renda fixa', 'tesouro direto', 'coe', 'fundos')
                OR UPPER(COALESCE(asset_class, '')) IN ('RENDA_FIXA', 'TESOURO_DIRETO', 'COE', 'FUNDOS')
              )
            ORDER BY id
            """,
            (uid,),
        ).fetchall()

        selected_assets: list[dict[str, Any]] = []
        filter_ids = {int(x) for x in (asset_ids or []) if int(x) > 0}
        excluded_ids = {int(x) for x in (exclude_asset_ids or []) if int(x) > 0}
        for row in rows:
            item = dict(row)
            if filter_ids and int(item["id"]) not in filter_ids:
                continue
            if excluded_ids and int(item["id"]) in excluded_ids:
                continue
            if only_auto and not _is_auto_rentability_type(item.get("rentability_type")):
                continue
            selected_assets.append(item)

        if reset_from_principal:
            for asset in selected_assets:
                principal = _to_decimal(asset.get("principal_amount"))
                if principal is None:
                    continue
                base_date = _resolve_base_date(conn, asset)
                _exec(conn, 
                    """
                    UPDATE assets
                    SET current_value = ?, last_update = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (float(principal.quantize(_CURRENT_Q, rounding=ROUND_HALF_UP)), base_date.isoformat(), int(asset["id"]), uid),
                )

    results: list[dict[str, Any]] = []
    updated = 0
    skipped = 0
    errors = 0

    for asset in selected_assets:
        res = update_investment_value(int(asset["id"]), as_of_date=as_of.isoformat(), user_id=uid)
        results.append(res)
        if not res.get("ok", False):
            errors += 1
        elif res.get("updated", False):
            updated += 1
        else:
            skipped += 1

    return {
        "ok": True,
        "as_of_date": as_of.isoformat(),
        "only_auto": bool(only_auto),
        "reset_from_principal": bool(reset_from_principal),
        "excluded_assets": sorted(excluded_ids),
        "total_assets": len(selected_assets),
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }


def preview_divergence_report(
    as_of_date: str | None = None,
    user_id: int | None = None,
    only_auto: bool = True,
    threshold_pct: float = 0.0,
    limit: int = 200,
) -> dict[str, Any]:
    uid = _uid(user_id)
    as_of = _parse_date(as_of_date, "as_of_date") if as_of_date else _date.today()
    threshold = abs(float(threshold_pct or 0.0))
    max_rows = max(1, int(limit or 200))

    with get_conn() as conn:
        rows = _exec(conn, 
            """
            SELECT
                id, symbol, name, user_id, created_at, asset_class, rentability_type, index_name,
                index_pct, spread_rate, fixed_rate, principal_amount, current_value, last_update
            FROM assets
            WHERE user_id = ?
              AND (
                LOWER(REPLACE(COALESCE(asset_class, ''), '_', ' ')) IN ('renda fixa', 'tesouro direto', 'coe', 'fundos')
                OR UPPER(COALESCE(asset_class, '')) IN ('RENDA_FIXA', 'TESOURO_DIRETO', 'COE', 'FUNDOS')
              )
            ORDER BY id
            """,
            (uid,),
        ).fetchall()

        report_rows: list[dict[str, Any]] = []
        for row in rows:
            asset = dict(row)
            if only_auto and not _is_auto_rentability_type(asset.get("rentability_type")):
                continue

            stored = _to_decimal(asset.get("current_value"))
            sim = _simulate_asset_value(conn, asset, as_of)
            if not sim.get("ok", False):
                report_rows.append(
                    {
                        "asset_id": int(asset["id"]),
                        "symbol": asset.get("symbol"),
                        "rentability_type": _norm_rentability_type(asset.get("rentability_type")),
                        "ok": False,
                        "reason": sim.get("reason"),
                    }
                )
                continue

            projected = _to_decimal(sim.get("current_value"), Decimal("0")) or Decimal("0")
            stored_val = stored if stored is not None else Decimal("0")
            delta = projected - stored_val
            delta_pct = None
            if stored_val != 0:
                delta_pct = float((delta / stored_val) * Decimal("100"))
            elif projected != 0:
                delta_pct = 100.0
            else:
                delta_pct = 0.0

            if abs(delta_pct) < threshold:
                continue

            report_rows.append(
                {
                    "asset_id": int(asset["id"]),
                    "symbol": asset.get("symbol"),
                    "name": asset.get("name"),
                    "rentability_type": _norm_rentability_type(asset.get("rentability_type")),
                    "stored_current_value": float(stored_val),
                    "projected_current_value": float(projected.quantize(_CURRENT_Q, rounding=ROUND_HALF_UP)),
                    "delta_value": float(delta.quantize(_CURRENT_Q, rounding=ROUND_HALF_UP)),
                    "delta_pct": float(round(delta_pct, 6)),
                    "projected_last_update": sim.get("last_update"),
                    "reason": sim.get("reason"),
                    "ok": True,
                }
            )

        report_rows.sort(key=lambda r: abs(float(r.get("delta_pct", 0.0))), reverse=True)
        trimmed = report_rows[:max_rows]
        return {
            "ok": True,
            "as_of_date": as_of.isoformat(),
            "only_auto": bool(only_auto),
            "threshold_pct": threshold,
            "total_rows": len(trimmed),
            "rows": trimmed,
        }

