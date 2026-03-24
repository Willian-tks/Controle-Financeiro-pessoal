from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, time
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from zoneinfo import ZoneInfo

import auth
import invest_quotes
import invest_repo
from tenant import clear_tenant_context, set_current_user_id, set_current_workspace_id


DEFAULT_TZ = "America/Sao_Paulo"
DEFAULT_START_TIME = time(hour=10, minute=0)
DEFAULT_END_TIME = time(hour=17, minute=10)
DEFAULT_LOCK_FILE = "/tmp/domus-update-quotes.lock"


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float | None) -> float | None:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_hhmm(raw: str | None, fallback: time) -> time:
    value = str(raw or "").strip()
    if not value:
        return fallback
    try:
        hour_s, minute_s = value.split(":", 1)
        hour = max(0, min(23, int(hour_s)))
        minute = max(0, min(59, int(minute_s)))
        return time(hour=hour, minute=minute)
    except Exception:
        return fallback


def _now_in_market_window(now: datetime, *, start_at: time, end_at: time) -> bool:
    if now.weekday() >= 5:
        return False
    current = now.timetz().replace(tzinfo=None)
    return start_at <= current <= end_at


@contextmanager
def _single_run_lock(lock_path: str):
    lock_file = None
    try:
        lock_dir = Path(lock_path).expanduser().resolve().parent
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "w", encoding="utf-8")
        if fcntl is None:
            yield
            return
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        yield
    finally:
        if lock_file is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            lock_file.close()


def _iter_target_workspaces() -> list[dict]:
    rows = auth.list_all_workspaces() or []
    return [ws for ws in rows if str(ws.get("workspace_status") or "").strip().lower() == "active"]


def run_job(
    *,
    force: bool = False,
    timeout_s: float | None = None,
    max_workers: int | None = None,
    timezone_name: str = DEFAULT_TZ,
    start_at: time = DEFAULT_START_TIME,
    end_at: time = DEFAULT_END_TIME,
) -> dict:
    tz = ZoneInfo(timezone_name)
    now = datetime.now(tz)
    if not force and not _now_in_market_window(now, start_at=start_at, end_at=end_at):
        return {
            "ok": True,
            "skipped": True,
            "reason": "outside_market_window",
            "now": now.isoformat(),
            "timezone": timezone_name,
        }

    summary = {
        "ok": True,
        "skipped": False,
        "timezone": timezone_name,
        "started_at": now.isoformat(),
        "workspace_count": 0,
        "processed_workspaces": 0,
        "skipped_workspaces": 0,
        "assets_total": 0,
        "quotes_total": 0,
        "saved_total": 0,
        "error_total": 0,
        "workspaces": [],
    }

    workspaces = _iter_target_workspaces()
    summary["workspace_count"] = len(workspaces)

    for ws in workspaces:
        workspace_id = int(ws.get("workspace_id") or 0)
        owner_user_id = int(ws.get("owner_user_id") or 0)
        workspace_info = {
            "workspace_id": workspace_id,
            "workspace_name": ws.get("workspace_name"),
            "owner_user_id": owner_user_id,
            "assets": 0,
            "quotes": 0,
            "saved": 0,
            "errors": 0,
            "skipped": False,
        }

        if workspace_id <= 0 or owner_user_id <= 0:
            workspace_info["skipped"] = True
            workspace_info["skip_reason"] = "missing_scope"
            summary["skipped_workspaces"] += 1
            summary["workspaces"].append(workspace_info)
            continue

        try:
            set_current_workspace_id(workspace_id)
            set_current_user_id(owner_user_id)
            invest_repo.upsert_quote_job_status(
                workspace_id=workspace_id,
                last_started_at=now.isoformat(),
                last_finished_at=None,
                last_status="running",
                last_reason=None,
                last_saved_total=0,
                last_total=0,
                last_error_total=0,
                last_run_scope="automatic",
            )
            assets = [dict(a) for a in (invest_repo.list_assets(user_id=owner_user_id) or [])]
            workspace_info["assets"] = len(assets)
            summary["assets_total"] += len(assets)

            if not assets:
                workspace_info["skipped"] = True
                workspace_info["skip_reason"] = "no_assets"
                invest_repo.upsert_quote_job_status(
                    workspace_id=workspace_id,
                    last_started_at=now.isoformat(),
                    last_finished_at=datetime.now(tz).isoformat(),
                    last_status="skipped",
                    last_reason="no_assets",
                    last_saved_total=0,
                    last_total=0,
                    last_error_total=0,
                    last_run_scope="automatic",
                )
                summary["skipped_workspaces"] += 1
                summary["workspaces"].append(workspace_info)
                continue

            report = invest_quotes.update_all_prices(
                assets=assets,
                timeout_s=timeout_s,
                max_workers=max_workers,
            )
            workspace_info["quotes"] = len(report)
            summary["quotes_total"] += len(report)

            for row in report:
                if not row.get("ok"):
                    workspace_info["errors"] += 1
                    continue
                invest_repo.upsert_price(
                    asset_id=int(row["asset_id"]),
                    date=str(row["px_date"]),
                    price=float(row["price"]),
                    source=row.get("src") or "auto_job",
                    user_id=owner_user_id,
                )
                workspace_info["saved"] += 1

            summary["processed_workspaces"] += 1
            summary["saved_total"] += workspace_info["saved"]
            summary["error_total"] += workspace_info["errors"]
            invest_repo.upsert_quote_job_status(
                workspace_id=workspace_id,
                last_started_at=now.isoformat(),
                last_finished_at=datetime.now(tz).isoformat(),
                last_status="success" if workspace_info["errors"] == 0 else "warning",
                last_reason=None,
                last_saved_total=workspace_info["saved"],
                last_total=workspace_info["quotes"],
                last_error_total=workspace_info["errors"],
                last_run_scope="automatic",
            )
            summary["workspaces"].append(workspace_info)
        except Exception as exc:
            workspace_info["errors"] += 1
            workspace_info["error"] = str(exc)
            summary["error_total"] += 1
            if workspace_id > 0:
                invest_repo.upsert_quote_job_status(
                    workspace_id=workspace_id,
                    last_started_at=now.isoformat(),
                    last_finished_at=datetime.now(tz).isoformat(),
                    last_status="error",
                    last_reason=str(exc),
                    last_saved_total=workspace_info["saved"],
                    last_total=workspace_info["quotes"],
                    last_error_total=workspace_info["errors"],
                    last_run_scope="automatic",
                )
            summary["workspaces"].append(workspace_info)
        finally:
            clear_tenant_context()

    summary["finished_at"] = datetime.now(tz).isoformat()
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atualiza cotações de investimentos por workspace.")
    parser.add_argument("--force", action="store_true", help="Executa fora da janela de mercado.")
    parser.add_argument("--timeout-s", type=float, default=_env_float("QUOTE_JOB_TIMEOUT_S", None))
    parser.add_argument("--max-workers", type=int, default=_env_int("QUOTE_JOB_MAX_WORKERS", 0) or None)
    parser.add_argument("--timezone", default=os.getenv("QUOTE_JOB_TZ", DEFAULT_TZ))
    parser.add_argument("--start-at", default=os.getenv("QUOTE_JOB_START_AT", "10:00"))
    parser.add_argument("--end-at", default=os.getenv("QUOTE_JOB_END_AT", "17:10"))
    parser.add_argument("--lock-file", default=os.getenv("QUOTE_JOB_LOCK_FILE", DEFAULT_LOCK_FILE))
    args = parser.parse_args(argv)

    try:
        with _single_run_lock(args.lock_file):
            summary = run_job(
                force=bool(args.force),
                timeout_s=args.timeout_s,
                max_workers=args.max_workers,
                timezone_name=str(args.timezone or DEFAULT_TZ),
                start_at=_parse_hhmm(args.start_at, DEFAULT_START_TIME),
                end_at=_parse_hhmm(args.end_at, DEFAULT_END_TIME),
            )
    except BlockingIOError:
        summary = {
            "ok": True,
            "skipped": True,
            "reason": "already_running",
        }
    except Exception as exc:
        summary = {
            "ok": False,
            "error": str(exc),
        }

    print(json.dumps(summary, ensure_ascii=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
