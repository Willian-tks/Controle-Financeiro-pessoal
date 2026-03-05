from __future__ import annotations

import os
from collections import Counter, deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any


_MAX_EVENTS = max(50, int(os.getenv("SECURITY_MONITOR_MAX_EVENTS", "300")))
_EVENTS: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)
_COUNTS_BY_STATUS: Counter[int] = Counter()
_COUNTS_BY_TYPE: Counter[str] = Counter()
_LOCK = Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_event(
    *,
    event_type: str,
    status_code: int,
    path: str,
    detail: str,
    user_id: int | None = None,
    workspace_id: int | None = None,
    ip: str | None = None,
) -> None:
    row = {
        "ts": _utc_now_iso(),
        "event_type": str(event_type or "").strip() or "unknown",
        "status_code": int(status_code),
        "path": str(path or "").strip() or "-",
        "detail": str(detail or "").strip() or "-",
        "user_id": int(user_id) if user_id is not None else None,
        "workspace_id": int(workspace_id) if workspace_id is not None else None,
        "ip": str(ip or "").strip() or None,
    }
    with _LOCK:
        _EVENTS.append(row)
        _COUNTS_BY_STATUS[int(status_code)] += 1
        _COUNTS_BY_TYPE[row["event_type"]] += 1


def snapshot(limit: int = 50) -> dict[str, Any]:
    n = max(1, min(int(limit or 50), _MAX_EVENTS))
    with _LOCK:
        recent = list(_EVENTS)[-n:]
        return {
            "max_events": _MAX_EVENTS,
            "total_events": int(sum(_COUNTS_BY_STATUS.values())),
            "counts_by_status": {str(k): int(v) for k, v in sorted(_COUNTS_BY_STATUS.items(), key=lambda kv: kv[0])},
            "counts_by_type": {k: int(v) for k, v in sorted(_COUNTS_BY_TYPE.items(), key=lambda kv: kv[0])},
            "recent_events": recent,
        }


def reset() -> None:
    with _LOCK:
        _EVENTS.clear()
        _COUNTS_BY_STATUS.clear()
        _COUNTS_BY_TYPE.clear()
