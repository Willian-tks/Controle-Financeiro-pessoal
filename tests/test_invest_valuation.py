import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, Mock

import db
import invest_fx
import invest_reports
from api.main import invest_portfolio, invest_summary, _build_investments_report_html
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
            conn.execute("INSERT INTO users(id, email, password_hash, display_name, role, is_active) VALUES (9001, 'fx@test.invalid', 'x', 'Test', 'user', 1)")
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

    def test_fx_changes_market_not_cost_and_history_matches(self):
        self.seed_fx()
        pos, _, _ = invest_reports.portfolio_view(date_to="2026-01-10", user_id=9001)
        usd = pos[pos.asset_id == 8001].iloc[0]
        brl = pos[pos.asset_id == 8002].iloc[0]
        self.assertAlmostEqual(1015, usd.cost_basis)
        self.assertAlmostEqual(1440, usd.market_value)
        self.assertEqual("2026-01-09", usd.fx_ref_date)
        self.assertEqual(invest_fx.SOURCE, usd.fx_source)
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
