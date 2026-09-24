"""Read-only legacy diagnostics. This tool deliberately has no repair mode."""
import json
import math
from db import get_conn


def audit():
    issues = []
    with get_conn() as conn:
        rows = conn.execute("""SELECT t.id, t.asset_id, t.workspace_id, t.exchange_rate,
            t.quantity, t.price, t.fees, t.taxes, a.currency
            FROM trades t JOIN assets a ON a.id = t.asset_id
            ORDER BY t.id""").fetchall()
    for item in rows:
        row = dict(item)
        reasons = []
        currency = str(row["currency"] or "").strip().upper()
        for key in ("quantity", "price", "fees", "taxes"):
            try:
                value = float(row[key] or 0)
                if not math.isfinite(value) or value < 0 or (key in {"quantity", "price"} and value == 0):
                    reasons.append(f"{key}: valor inválido")
            except (ValueError, TypeError):
                reasons.append(f"{key}: valor inválido")
        if currency == "USD":
            try:
                fx = float(row["exchange_rate"] or 0)
                if not math.isfinite(fx) or fx <= 0:
                    reasons.append("câmbio ausente/inválido")
                elif fx == 1:
                    reasons.append("câmbio 1: conferir comprovante (não implica erro)")
            except (TypeError, ValueError):
                reasons.append("câmbio inválido")
        elif currency != "BRL":
            reasons.append("moeda fora da cobertura BRL/USD")
        if reasons:
            issues.append({"trade_id": row["id"], "asset_id": row["asset_id"],
                           "workspace_id": row["workspace_id"], "reasons": reasons})
    return {"trades_checked": len(rows), "issues": issues, "changed": 0}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
