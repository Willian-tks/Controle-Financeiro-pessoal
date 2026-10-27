import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, Mock

import db
import invest_fx
import invest_reports
import invest_repo
from api.main import invest_portfolio, invest_summary, _build_investments_report_html, _prepare_fixed_income_trade, _is_fixed_income_asset
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from tenant import clear_tenant_context, set_current_workspace_id


class ValuationContract:
    """The same assertions run on SQLite locally and PostgreSQL in CI."""
    def setUp(self):
        clear_tenant_context()
        with db.get_conn() as conn:
            for table in ("investment_fx_rates", "prices", "asset_prices", "trades", "income_events",
                          "assets", "workspace_users", "workspaces", "users"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                "INSERT INTO users(id, email, password_hash, display_name, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (9001, "fx@test.invalid", "x", "Test", "user", True),
            )
            conn.execute("INSERT INTO workspaces(id, name, owner_user_id, status) VALUES (7001, 'FX Test', 9001, 'active')")
            conn.execute("INSERT INTO workspaces(id, name, owner_user_id, status) VALUES (7002, 'Other', 9001, 'active')")
            for asset_id, currency, workspace in [(8001, "USD", 7001), (8002, "BRL", 7001), (8003, "USD", 7002)]:
                conn.execute("INSERT INTO assets(id, symbol, name, asset_class, currency, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (asset_id, f"A{asset_id}", "Test", "ETFs US" if currency == "USD" else "ETFs BR", currency, 9001, workspace))
            # Cost: 2 * 100 * 5 + (2 fees + 1 tax) * 5 = BRL 1015.
            for asset_id, workspace in [(8001, 7001), (8002, 7001), (8003, 7002)]:
                conn.execute("INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (asset_id, "2026-01-05", "BUY", 2, 100, 5, 2, 1, 9001, workspace))
                conn.execute("INSERT INTO prices(asset_id, date, price, source, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                             (asset_id, "2026-01-09", 120, "test", 9001, workspace))
        set_current_workspace_id(7001)

    def tearDown(self):
        clear_tenant_context()

    def seed_fx(self):
        with patch("invest_fx.fetch_ptax", return_value={"2026-01-09": 6.0, "2026-01-12": 7.0}):
            invest_fx.refresh_rates("2026-01-01", "2026-01-12")

    def _seed_review_asset(self, aid, asset_class, currency="BRL", mode="MANUAL"):
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO assets(id, symbol, name, asset_class, currency, rentability_type, principal_amount, current_value, last_update, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, f"REVIEW{aid}", "Synthetic review", asset_class, currency, mode,
                 48000, 49181.03, "2026-10-26", 9001, 7001),
            )
            for tid, day, amount in ((aid * 10, "2026-10-01", 38000), (aid * 10 + 1, "2026-10-26", 10000)):
                conn.execute(
                    "INSERT INTO trades(id, asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (tid, aid, day, "BUY", 1, amount, 5 if currency == "USD" else 1, 0, 0, 9001, 7001),
                )
            for day in ("2026-10-25", "2026-10-27"):
                conn.execute(
                    "INSERT INTO asset_prices(asset_id, px_date, price, source, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, day, 39181.03, "manual_current_value", 9001, 7001),
                )

    def test_all_balance_classes_prefer_live_balance_and_preserve_history(self):
        classes = ["Renda Fixa", "Tesouro Direto", "Coe", "Fundos"]
        ids = []
        for index, (label, mode) in enumerate((label, mode) for label in classes for mode in ("MANUAL", "PCT_CDI")):
            aid = 8100 + index
            ids.append(aid)
            self._seed_review_asset(aid, label, mode=mode)
        with patch("invest_fx.today", return_value=date(2026, 10, 27)):
            pos, _, _ = invest_reports.portfolio_view(user_id=9001)
            for aid in ids:
                with self.subTest(asset_id=aid, state="live"):
                    row = pos[pos.asset_id == aid].iloc[0]
                    self.assertAlmostEqual(49181.03, row.market_value)
                    self.assertAlmostEqual(48000, row.cost_basis)
            past, _, _ = invest_reports.portfolio_view(date_to="2026-10-25", user_id=9001)
            for aid in ids:
                with self.subTest(asset_id=aid, state="historical"):
                    row = past[past.asset_id == aid].iloc[0]
                    self.assertAlmostEqual(39181.03, row.market_value)
                    self.assertAlmostEqual(38000, row.cost_basis)
            summary = invest_summary(user={"id": 9001})
            self.assertAlmostEqual(float(pos.market_value.sum()), summary["total_market"])
            history = invest_reports.investments_value_timeseries("2026-10-27", "2026-10-27", user_id=9001)
            self.assertAlmostEqual(float(pos.market_value.sum()), history.iloc[0].invest_market_value)
            html = _build_investments_report_html(asset_class="Renda Fixa", date_from="2026-10-01", date_to="2026-10-27", user_id=9001)
            self.assertIn("49.181,03", html)

    def test_historical_same_day_snapshot_is_preserved_for_all_balance_classes(self):
        ids = []
        for index, label in enumerate(("Renda Fixa", "Tesouro Direto", "Coe", "Fundos")):
            aid = 8400 + index
            ids.append(aid)
            self._seed_review_asset(aid, label)
            with db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO asset_prices(asset_id, px_date, price, source, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, "2026-10-26", 39181.03, "manual_current_value", 9001, 7001),
                )
        with patch("invest_fx.today", return_value=date(2026, 10, 28)):
            pos, _, _ = invest_reports.portfolio_view(date_to="2026-10-26", user_id=9001)
            for aid in ids:
                with self.subTest(asset_id=aid):
                    self.assertAlmostEqual(39181.03, pos[pos.asset_id == aid].iloc[0].market_value)

    def test_live_balance_respects_future_dates_and_independent_snapshots(self):
        ids = []
        for index, label in enumerate(("Renda Fixa", "Tesouro Direto", "Coe", "Fundos")):
            aid = 8500 + index
            ids.append(aid)
            self._seed_review_asset(aid, label)
        for reference, source in (("2026-10-28", "manual_current_value"),
                                  ("2026-10-26", "independent_manual")):
            with db.get_conn() as conn:
                for aid in ids:
                    conn.execute("UPDATE assets SET last_update = ? WHERE id = ?", (reference, aid))
                    conn.execute("UPDATE asset_prices SET source = ? WHERE asset_id = ?", (source, aid))
            with patch("invest_fx.today", return_value=date(2026, 10, 27)):
                pos, _, _ = invest_reports.portfolio_view(user_id=9001)
                for aid in ids:
                    with self.subTest(asset_id=aid, reference=reference, source=source):
                        row = pos[pos.asset_id == aid].iloc[0]
                        self.assertAlmostEqual(39181.03, row.market_value)
                        self.assertEqual(source, row.price_source)

    def test_all_market_classes_ignore_balance_and_total_value_snapshots(self):
        labels = [label for label in invest_repo.ASSET_CLASSES
                  if label not in {"Renda Fixa", "Tesouro Direto", "Coe", "Fundos"}]
        expected = {}
        for index, label in enumerate(labels):
            aid = 8200 + index
            currency = "USD" if label in {"Stocks US", "ETFs US", "Cripto"} else "BRL"
            self._seed_review_asset(aid, label, currency)
            expected[aid] = (currency, label)
            with db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO prices(asset_id, date, price, source, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (aid, "2026-10-27", 25000, "test_provider", 9001, 7001),
                )
        self.seed_fx()
        with patch("invest_fx.today", return_value=date(2026, 10, 27)):
            pos, _, _ = invest_reports.portfolio_view(user_id=9001)
            for aid, (currency, label) in expected.items():
                with self.subTest(asset_class=label, state="quoted"):
                    row = pos[pos.asset_id == aid].iloc[0]
                    self.assertAlmostEqual(50000 * (7 if currency == "USD" else 1), row.market_value)
                    self.assertAlmostEqual(48000 * (5 if currency == "USD" else 1), row.cost_basis)
                    self.assertEqual("cotacao", row.value_origin)
            with db.get_conn() as conn:
                for aid in expected:
                    conn.execute("DELETE FROM prices WHERE asset_id = ?", (aid,))
            pos, _, _ = invest_reports.portfolio_view(user_id=9001)
            for aid, (_, label) in expected.items():
                with self.subTest(asset_class=label, state="without_quote"):
                    row = pos[pos.asset_id == aid].iloc[0]
                    self.assertAlmostEqual(row.cost_basis, row.market_value)
                    self.assertEqual("custo_medio", row.value_origin)

    def test_balance_class_redemptions_do_not_resurrect_snapshot_value(self):
        ids = []
        for index, label in enumerate(("Renda Fixa", "Tesouro Direto", "Coe", "Fundos")):
            aid = 8300 + index
            ids.append(aid)
            self._seed_review_asset(aid, label)
            with db.get_conn() as conn:
                conn.execute(
                    "INSERT INTO trades(id, asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id, workspace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (aid * 10 + 2, aid, "2026-10-27", "SELL", 0.5, 20000, 1, 0, 0, 9001, 7001),
                )
                conn.execute("UPDATE assets SET current_value = ?, last_update = ? WHERE id = ?",
                             (39181.03, "2026-10-27", aid))
                conn.execute("UPDATE asset_prices SET price = ? WHERE asset_id = ? AND px_date = ?",
                             (49181.03, aid, "2026-10-27"))
        with patch("invest_fx.today", return_value=date(2026, 10, 27)):
            pos, _, _ = invest_reports.portfolio_view(user_id=9001)
            for aid in ids:
                with self.subTest(asset_id=aid, state="partial"):
                    self.assertAlmostEqual(39181.03, pos[pos.asset_id == aid].iloc[0].market_value)
            with db.get_conn() as conn:
                for aid in ids:
                    conn.execute("UPDATE trades SET quantity = ? WHERE id = ?", (2, aid * 10 + 2))
                    conn.execute("UPDATE assets SET current_value = 0 WHERE id = ?", (aid,))
            pos, _, _ = invest_reports.portfolio_view(user_id=9001)
            for aid in ids:
                with self.subTest(asset_id=aid, state="closed"):
                    row = pos[pos.asset_id == aid].iloc[0]
                    self.assertAlmostEqual(0, row.qty)
                    self.assertAlmostEqual(0, row.market_value)
                    self.assertAlmostEqual(0, row.cost_basis)

    def test_classification_and_backdated_cash_flows_share_balance_rules(self):
        balance_classes = {"Renda Fixa", "Tesouro Direto", "Coe", "Fundos"}
        for label in invest_repo.ASSET_CLASSES:
            with self.subTest(asset_class=label):
                self.assertEqual(label in balance_classes, _is_fixed_income_asset({"asset_class": label}))
        for label in balance_classes:
            asset = {"id": 1, "asset_class": label, "principal_amount": 48000,
                     "current_value": 49181.03, "last_update": "2026-10-27"}
            for side, amount in (("BUY", 10000), ("SELL", 1000)):
                with self.subTest(asset_class=label, side=side), patch(
                    "api.main._get_asset_trade_position", return_value={"qty": 2, "cost_basis": 48000}
                ):
                    result = _prepare_fixed_income_trade(
                        asset=asset, side=side, quantity=1, price=amount,
                        trade_date="2026-10-26", user_id=9001,
                    )
                    expected = 49181.03 + (amount if side == "BUY" else -amount)
                    self.assertAlmostEqual(expected, result["current_value"])
                    self.assertEqual("2026-10-27", result["last_update"])

    def test_fx_changes_market_not_cost_and_history_matches(self):
        self.seed_fx()
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        usd = pos[pos.asset_id == 8001].iloc[0]
        brl = pos[pos.asset_id == 8002].iloc[0]
        self.assertAlmostEqual(1015, usd.cost_basis)
        self.assertAlmostEqual(1440, usd.market_value)
        self.assertEqual("2026-01-09", usd.fx_ref_date)
        self.assertEqual(invest_fx.SOURCE, usd.fx_source)
        self.assertEqual("test", usd.price_source)
        self.assertAlmostEqual(203, brl.cost_basis)
        self.assertAlmostEqual(240, brl.market_value)
        self.assertEqual({8001, 8002}, set(pos.asset_id))
        history = invest_reports.investments_value_timeseries("2026-01-10", "2026-01-10", user_id=9001)
        self.assertAlmostEqual(pos.market_value.sum(), history.iloc[0].invest_market_value)
        later, _, _ = invest_reports.portfolio_view(date_to="2026-01-12", user_id=9001)
        self.assertAlmostEqual(1680, later[later.asset_id == 8001].iloc[0].market_value)
        self.assertAlmostEqual(1015, later[later.asset_id == 8001].iloc[0].cost_basis)

    def test_no_quote_never_converts_brl_cost_again(self):
        self.seed_fx()
        with db.get_conn() as conn:
            conn.execute("DELETE FROM prices WHERE asset_id = 8001")
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        row = pos[pos.asset_id == 8001].iloc[0]
        self.assertAlmostEqual(1015, row.market_value)
        self.assertEqual("custo_medio", row.value_origin)
        self.assertEqual("custo_medio", row.price_source)
        self.assertIn("estimado", row.valuation_warning)

    def test_missing_and_stale_fx_are_explicit(self):
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        row = pos[pos.asset_id == 8001].iloc[0]
        self.assertAlmostEqual(1200, row.market_value)
        self.assertIn("Sem PTAX", row.valuation_warning)
        self.seed_fx()
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-20", user_id=9001)
        self.assertIn("Câmbio sem atualização", pos[pos.asset_id == 8001].iloc[0].valuation_warning)

    def test_partial_and_closed_position_fees_and_taxes(self):
        self.seed_fx()
        with db.get_conn() as conn:
            conn.execute("INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id, workspace_id) VALUES (8001, '2026-01-10', 'SELL', 1, 130, 5.5, 2, 1, 9001, 7001)")
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        row = pos[pos.asset_id == 8001].iloc[0]
        self.assertAlmostEqual(507.5, row.cost_basis)
        self.assertAlmostEqual((130 - 3) * 5.5 - 507.5, row.realized_pnl)
        self.assertAlmostEqual(720, row.market_value)
        with db.get_conn() as conn:
            conn.execute("INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id, workspace_id) VALUES (8001, '2026-01-11', 'SELL', 1, 130, 5.5, 0, 0, 9001, 7001)")
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-11", user_id=9001)
        row = pos[pos.asset_id == 8001].iloc[0]
        self.assertAlmostEqual(0, row.cost_basis)
        self.assertAlmostEqual(0, row.market_value)

    def test_api_summary_report_and_workspace_scope(self):
        self.seed_fx()
        with patch("invest_fx.today", return_value=date(2026, 1, 10)):
            portfolio = invest_portfolio(user={"id": 9001})
            JSONResponse(jsonable_encoder(portfolio))  # no NaN/NaT response values
            summary = invest_summary(user={"id": 9001})
            self.assertAlmostEqual(sum(p["market_value"] for p in portfolio["positions"]), summary["total_market"])
        html = _build_investments_report_html(asset_class=None, date_from="2026-01-01", date_to="2026-01-10", user_id=9001)
        self.assertIn(invest_fx.SOURCE, html)
        self.assertIn("1.440,00", html)
        set_current_workspace_id(7002)
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        self.assertEqual({8003}, set(pos.asset_id))

    def test_legacy_audit_does_not_repair_trades(self):
        from audit_investments import audit
        with db.get_conn() as conn:
            conn.execute("UPDATE trades SET exchange_rate = 1 WHERE asset_id = 8001")
        result = audit()
        self.assertEqual(0, result["changed"])
        self.assertEqual(1, len(result["issues"]))
        with db.get_conn() as conn:
            row = conn.execute("SELECT exchange_rate FROM trades WHERE asset_id = 8001").fetchone()
            self.assertEqual(1, row["exchange_rate"])

    def test_empty_portfolio_is_valid_json(self):
        with db.get_conn() as conn:
            conn.execute("DELETE FROM trades")
        self.assertEqual([], invest_portfolio(user={"id": 9001})["positions"])
        self.assertEqual(0, invest_summary(user={"id": 9001})["total_market"])

    def test_provider_failure_preserves_cache(self):
        self.seed_fx()
        before = invest_fx.load_rates()
        with patch("invest_fx.fetch_ptax", side_effect=ValueError("unavailable")):
            self.assertFalse(invest_fx.refresh_for_assets([{"currency": "USD"}])["ok"])
        self.assertEqual(before, invest_fx.load_rates())


class SQLiteValuationTests(ValuationContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.original = db.SQLITE_PATH, db.USE_POSTGRES
        db.SQLITE_PATH, db.USE_POSTGRES = Path(cls.temp.name) / "test.db", False
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        db.SQLITE_PATH, db.USE_POSTGRES = cls.original
        cls.temp.cleanup()


class PtaxProviderTests(unittest.TestCase):
    def test_only_valid_closing_quotes_are_used(self):
        response = Mock()
        response.json.return_value = {"value": [
            {"tipoBoletim": "Abertura", "dataHoraCotacao": "2026-01-09 10:00", "cotacaoVenda": 9},
            {"tipoBoletim": "Fechamento", "dataHoraCotacao": "2026-01-09 13:00", "cotacaoVenda": 6},
        ]}
        with patch("invest_fx.requests.get", return_value=response) as request:
            self.assertEqual({"2026-01-09": 6}, invest_fx.fetch_ptax(date(2026, 1, 9), date(2026, 1, 10)))
            self.assertNotIn("+", request.call_args.kwargs["params"])
        for rate in (0, -1, float("nan"), float("inf")):
            response.json.return_value["value"][1]["cotacaoVenda"] = rate
            with patch("invest_fx.requests.get", return_value=response), self.assertRaises(ValueError):
                invest_fx.fetch_ptax(date(2026, 1, 9), date(2026, 1, 10))
