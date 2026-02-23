from __future__ import annotations

import io
from typing import Any

import pandas as pd

import invest_repo
import repo
import reports


def _read_csv_flexible(raw_bytes: bytes) -> pd.DataFrame:
    text = raw_bytes.decode("utf-8-sig", errors="ignore")
    try:
        return pd.read_csv(io.StringIO(text), sep=None, engine="python")
    except Exception:
        return pd.read_csv(io.StringIO(text))


def normalize_transactions_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    required = {"date", "description", "amount", "account"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"CSV faltando colunas obrigatórias: {sorted(list(missing))}")

    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["description"] = out["description"].astype(str).str.strip()
    out["account"] = out["account"].astype(str).str.strip()
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")

    for opt in ["category", "method", "notes"]:
        if opt not in out.columns:
            out[opt] = None
        else:
            out[opt] = out[opt].astype(str).replace({"nan": None}).where(out[opt].notna(), None)

    out = out.dropna(subset=["date", "description", "account", "amount"])
    out = out[(out["description"] != "") & (out["account"] != "")]
    return out[["date", "description", "amount", "account", "category", "method", "notes"]]


def _normalize_assets_df(df: pd.DataFrame) -> pd.DataFrame:
    alias = {
        "ticker/símbolo": "symbol",
        "ticker/simbolo": "symbol",
        "ticker": "symbol",
        "símbolo": "symbol",
        "simbolo": "symbol",
        "nome": "name",
        "classe": "asset_class",
        "setor": "sector",
        "sector": "sector",
        "moeda": "currency",
        "conta corretora (opcional)": "broker_account",
        "conta corretora": "broker_account",
        "conta origem (opcional)": "source_account",
        "conta origem": "source_account",
    }
    out = df.copy()
    out.columns = [str(c).replace("\ufeff", "").strip() for c in out.columns]
    out.columns = [alias.get(str(c).lower().strip(), str(c).lower().strip()) for c in out.columns]

    required = {"symbol", "name", "asset_class"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"CSV de ativos faltando colunas obrigatórias: {sorted(list(missing))}")

    if "currency" not in out.columns:
        out["currency"] = "BRL"
    if "sector" not in out.columns:
        out["sector"] = "Não definido"
    if "broker_account" not in out.columns:
        out["broker_account"] = None
    if "source_account" not in out.columns:
        out["source_account"] = None

    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["name"] = out["name"].astype(str).str.strip()
    out["asset_class"] = out["asset_class"].astype(str).str.strip()
    out["sector"] = out["sector"].astype(str).str.strip().replace({"": "Não definido"})
    out["currency"] = out["currency"].astype(str).str.strip().str.upper().replace({"": "BRL"})
    out["broker_account"] = out["broker_account"].astype(str).str.strip()
    out["source_account"] = out["source_account"].astype(str).str.strip()
    out = out[(out["symbol"] != "") & (out["name"] != "") & (out["asset_class"] != "")]
    return out[["symbol", "name", "asset_class", "sector", "currency", "broker_account", "source_account"]]


def _normalize_trades_df(df: pd.DataFrame) -> pd.DataFrame:
    alias = {
        "asset_id": "symbol",
        "asset": "symbol",
        "ativo": "symbol",
        "ticker": "symbol",
        "simbolo": "symbol",
        "símbolo": "symbol",
        "tipo": "side",
        "lado": "side",
        "quantidade": "quantity",
        "qtd": "quantity",
        "preco": "price",
        "preço": "price",
        "taxa": "fees",
        "taxas": "fees",
        "imposto": "taxes",
        "impostos": "taxes",
        "obs": "note",
        "observacao": "note",
        "observação": "note",
    }
    out = df.copy()
    out.columns = [str(c).replace("\ufeff", "").strip() for c in out.columns]
    out.columns = [alias.get(str(c).lower().strip(), str(c).lower().strip()) for c in out.columns]

    required = {"date", "symbol", "side", "quantity", "price"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"CSV de operações faltando colunas obrigatórias: {sorted(list(missing))}")

    if "fees" not in out.columns:
        out["fees"] = 0
    if "taxes" not in out.columns:
        out["taxes"] = 0
    if "note" not in out.columns:
        out["note"] = None

    out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    out["side"] = (
        out["side"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace(
            {
                "COMPRA": "BUY",
                "VENDA": "SELL",
                "C": "BUY",
                "V": "SELL",
            }
        )
    )

    def _to_num_mixed(series: pd.Series) -> pd.Series:
        raw = series.astype(str).str.strip()
        num = pd.to_numeric(raw, errors="coerce")
        # fallback para formato pt-BR (ex.: 1.234,56)
        mask = num.isna() & raw.ne("") & raw.ne("nan")
        if mask.any():
            raw_pt = raw[mask].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            num.loc[mask] = pd.to_numeric(raw_pt, errors="coerce")
        return num

    out["quantity"] = _to_num_mixed(out["quantity"])
    out["price"] = _to_num_mixed(out["price"])
    out["fees"] = _to_num_mixed(out["fees"]).fillna(0.0)
    out["taxes"] = _to_num_mixed(out["taxes"]).fillna(0.0)
    out["note"] = out["note"].astype(str).replace({"nan": None}).where(out["note"].notna(), None)
    out = out.dropna(subset=["date", "symbol", "side", "quantity", "price"])
    out = out[
        (out["symbol"] != "")
        & (out["side"].isin(["BUY", "SELL"]))
        & (out["quantity"] > 0)
        & (out["price"] > 0)
        & (out["fees"] >= 0)
        & (out["taxes"] >= 0)
    ]
    return out[["date", "symbol", "side", "quantity", "price", "fees", "taxes", "note"]]


def import_transactions_csv(raw_bytes: bytes, user_id: int, preview_only: bool = False) -> dict[str, Any]:
    raw = _read_csv_flexible(raw_bytes)
    norm = normalize_transactions_df(raw)
    if preview_only:
        return {
            "ok": True,
            "rows": int(len(norm)),
            "preview": norm.head(20).to_dict(orient="records"),
        }

    for acc in norm["account"].dropna().unique():
        repo.create_account(str(acc), "Banco", user_id=user_id)
    for cat in norm["category"].dropna().unique():
        if str(cat).strip():
            repo.create_category(str(cat), "Despesa", user_id=user_id)

    account_map = {r["name"]: int(r["id"]) for r in (repo.list_accounts(user_id=user_id) or [])}
    category_map = {r["name"]: int(r["id"]) for r in (repo.list_categories(user_id=user_id) or [])}

    inserted = 0
    for _, row in norm.iterrows():
        acc_id = account_map.get(str(row["account"]))
        cat_val = row["category"] if row["category"] is not None else None
        cat_id = category_map.get(str(cat_val)) if cat_val else None
        if not acc_id:
            continue
        repo.insert_transaction(
            date=str(row["date"]),
            description=str(row["description"]),
            amount=float(row["amount"]),
            account_id=int(acc_id),
            category_id=int(cat_id) if cat_id else None,
            method=(str(row["method"]).strip() if row["method"] is not None and str(row["method"]).strip() else None),
            notes=(str(row["notes"]).strip() if row["notes"] is not None and str(row["notes"]).strip() else None),
            user_id=user_id,
        )
        inserted += 1

    return {"ok": True, "rows": int(len(norm)), "inserted": int(inserted)}


def import_assets_csv(raw_bytes: bytes, user_id: int, preview_only: bool = False) -> dict[str, Any]:
    raw = _read_csv_flexible(raw_bytes)
    norm = _normalize_assets_df(raw)
    if preview_only:
        return {
            "ok": True,
            "rows": int(len(norm)),
            "preview": norm.head(20).to_dict(orient="records"),
        }

    acc_rows = repo.list_accounts(user_id=user_id) or []
    acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
    acc_name_to_type = {r["name"]: r["type"] for r in acc_rows}

    inserted = 0
    skipped = 0
    errors: list[str] = []
    for _, row in norm.iterrows():
        sym = str(row["symbol"]).strip().upper()
        nm = str(row["name"]).strip()
        cls = str(row["asset_class"]).strip()
        sector = str(row.get("sector", "Não definido")).strip() or "Não definido"
        cur = str(row.get("currency", "BRL")).strip().upper() or "BRL"
        broker_name = str(row.get("broker_account", "")).strip()
        source_name = str(row.get("source_account", "")).strip()

        broker_id = None
        if broker_name:
            if broker_name not in acc_name_to_id:
                repo.create_account(broker_name, "Corretora", user_id=user_id)
                acc_rows = repo.list_accounts(user_id=user_id) or []
                acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
                acc_name_to_type = {r["name"]: r["type"] for r in acc_rows}
            if acc_name_to_type.get(broker_name) != "Corretora":
                errors.append(f"{sym}: conta '{broker_name}' existe mas não é Corretora.")
                skipped += 1
                continue
            broker_id = acc_name_to_id.get(broker_name)

        source_id = None
        if source_name:
            if source_name not in acc_name_to_id:
                repo.create_account(source_name, "Banco", user_id=user_id)
                acc_rows = repo.list_accounts(user_id=user_id) or []
                acc_name_to_id = {r["name"]: int(r["id"]) for r in acc_rows}
            source_id = acc_name_to_id.get(source_name)

        try:
            created = invest_repo.create_asset(
                symbol=sym,
                name=nm,
                asset_class=cls,
                sector=sector,
                currency=cur,
                broker_account_id=broker_id,
                source_account_id=source_id,
                user_id=user_id,
            )
            if created:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append(f"{sym}: {e}")
            skipped += 1

    return {
        "ok": True,
        "rows": int(len(norm)),
        "inserted": int(inserted),
        "skipped": int(skipped),
        "errors": errors[:50],
    }


def import_trades_csv(raw_bytes: bytes, user_id: int, preview_only: bool = False) -> dict[str, Any]:
    raw = _read_csv_flexible(raw_bytes)
    norm = _normalize_trades_df(raw)
    if preview_only:
        return {
            "ok": True,
            "rows": int(len(norm)),
            "preview": norm.head(20).to_dict(orient="records"),
        }

    assets = invest_repo.list_assets(user_id=user_id) or []
    asset_by_symbol = {str(a["symbol"]).upper(): dict(a) for a in assets}
    cat_id = repo.ensure_category("Investimentos", "Transferencia", user_id=user_id)

    inserted = 0
    skipped = 0
    errors: list[str] = []

    for _, row in norm.iterrows():
        symbol = str(row["symbol"]).upper()
        asset = asset_by_symbol.get(symbol)
        if not asset:
            skipped += 1
            errors.append(f"{symbol}: ativo não encontrado.")
            continue

        broker_acc_id = asset.get("broker_account_id")
        if not broker_acc_id:
            skipped += 1
            errors.append(f"{symbol}: ativo sem conta corretora vinculada.")
            continue

        side = str(row["side"]).upper()
        qty = float(row["quantity"])
        price = float(row["price"])
        fees = float(row["fees"] or 0.0)
        taxes = float(row["taxes"] or 0.0)
        note = (str(row["note"]).strip() if row["note"] is not None and str(row["note"]).strip() else None)

        gross = qty * price
        total_cost = gross + fees + taxes
        broker_cash = reports.account_balance_by_id(int(broker_acc_id), user_id=user_id)
        if side == "BUY" and broker_cash < total_cost:
            skipped += 1
            errors.append(
                f"{symbol}: saldo insuficiente na corretora. Disponível {broker_cash:.2f}, necessário {total_cost:.2f}."
            )
            continue

        if side == "BUY":
            cash = -total_cost
            desc = f"INV BUY {symbol}"
        else:
            cash = +(gross - fees - taxes)
            desc = f"INV SELL {symbol}"

        repo.insert_transaction(
            date=str(row["date"]),
            description=desc,
            amount=float(cash),
            account_id=int(broker_acc_id),
            category_id=int(cat_id),
            method="INV",
            notes=note,
            user_id=user_id,
        )
        invest_repo.insert_trade(
            asset_id=int(asset["id"]),
            date=str(row["date"]),
            side=side,
            quantity=qty,
            price=price,
            fees=fees,
            taxes=taxes,
            note=note,
            user_id=user_id,
        )
        inserted += 1

    return {
        "ok": True,
        "rows": int(len(norm)),
        "inserted": int(inserted),
        "skipped": int(skipped),
        "errors": errors[:50],
    }
