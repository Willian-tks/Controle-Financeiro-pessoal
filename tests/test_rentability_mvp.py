import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fastapi import HTTPException

import db as db_module
import invest_rentability
from api.main import _validate_asset_rentability


class _IsolatedDbTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "finance_test.db"
        cls._orig_sqlite_path = db_module.SQLITE_PATH
        cls._orig_db_path = db_module.DB_PATH
        cls._orig_database_url = db_module.DATABASE_URL
        cls._orig_use_postgres = db_module.USE_POSTGRES

        db_module.DATABASE_URL = ""
        db_module.USE_POSTGRES = False
        db_module.SQLITE_PATH = cls._db_path
        db_module.DB_PATH = cls._db_path
        db_module.init_db()

    @classmethod
    def tearDownClass(cls):
        db_module.SQLITE_PATH = cls._orig_sqlite_path
        db_module.DB_PATH = cls._orig_db_path
        db_module.DATABASE_URL = cls._orig_database_url
        db_module.USE_POSTGRES = cls._orig_use_postgres
        cls._tmpdir.cleanup()

    def setUp(self):
        with db_module.get_conn() as conn:
            tables = [
                "credit_card_charges",
                "credit_card_invoices",
                "credit_cards",
                "asset_prices",
                "prices",
                "income_events",
                "trades",
                "index_rates",
                "assets",
                "transactions",
                "categories",
                "accounts",
                "invites",
                "users",
            ]
            for t in tables:
                conn.execute(f"DELETE FROM {t}")
            conn.execute(
                """
                INSERT INTO users(id, email, password_hash, display_name, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "test@example.com", "x", "Test", "user", 1),
            )
        self.uid = 1

    def _create_asset(
        self,
        *,
        symbol: str,
        asset_class: str = "Renda Fixa",
        rentability_type: str = "MANUAL",
        index_name=None,
        index_pct=None,
        spread_rate=None,
        fixed_rate=None,
        principal_amount=1000.0,
        current_value=1000.0,
        last_update=None,
        created_at="2026-01-01",
    ) -> int:
        with db_module.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO assets(
                    symbol, name, asset_class, sector, currency,
                    rentability_type, index_name, index_pct, spread_rate, fixed_rate,
                    principal_amount, current_value, last_update, created_at, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    f"Asset {symbol}",
                    asset_class,
                    "Não definido",
                    "BRL",
                    rentability_type,
                    index_name,
                    index_pct,
                    spread_rate,
                    fixed_rate,
                    principal_amount,
                    current_value,
                    last_update,
                    created_at,
                    self.uid,
                ),
            )
            return int(cur.lastrowid)

    def _insert_trade(self, *, asset_id: int, date: str, side: str = "BUY", quantity: float = 1.0, price: float = 1000.0):
        with db_module.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, note, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (asset_id, date, side, quantity, price, 1.0, 0.0, 0.0, None, self.uid),
            )

    def _insert_index_rate(self, *, index_name: str, ref_date: str, value: float):
        with db_module.get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO index_rates(index_name, ref_date, value, source, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (index_name, ref_date, value, "test", self.uid),
            )

    def _asset_row(self, asset_id: int) -> dict:
        with db_module.get_conn() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id = ? AND user_id = ?", (asset_id, self.uid)).fetchone()
            return dict(row) if row else {}


class RentabilityEngineTests(_IsolatedDbTestCase):
    def test_prefixado_updates_and_is_idempotent(self):
        asset_id = self._create_asset(
            symbol="RF_PREFIX",
            rentability_type="PREFIXADO",
            fixed_rate=12.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2026-01-02",
        )

        res = invest_rentability.update_investment_value(asset_id, as_of_date="2026-01-05", user_id=self.uid)
        self.assertTrue(res["ok"])
        self.assertTrue(res["updated"])
        self.assertEqual(res["rentability_type"], "PREFIXADO")
        self.assertEqual(res["last_update"], "2026-01-05")

        rate = invest_rentability._annual_pct_to_daily_rate(Decimal("12.0"))
        factor = invest_rentability._factor_from_rate(rate)
        expected = (Decimal("1000.0") * factor).quantize(invest_rentability._CURRENT_Q, rounding=ROUND_HALF_UP)
        self.assertAlmostEqual(float(expected), float(res["current_value"]), places=6)

        second = invest_rentability.update_investment_value(asset_id, as_of_date="2026-01-05", user_id=self.uid)
        self.assertTrue(second["ok"])
        self.assertFalse(second["updated"])
        self.assertEqual(second["reason"], "already_up_to_date")

        row = self._asset_row(asset_id)
        self.assertEqual(row.get("last_update"), "2026-01-05")
        self.assertAlmostEqual(float(expected), float(row.get("current_value")), places=6)

    def test_pct_cdi_missing_index_data_keeps_value(self):
        asset_id = self._create_asset(
            symbol="RF_CDI_MISS",
            rentability_type="PCT_CDI",
            index_name="CDI",
            index_pct=100.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2026-01-02",
        )

        res = invest_rentability.update_investment_value(asset_id, as_of_date="2026-01-05", user_id=self.uid)
        self.assertTrue(res["ok"])
        self.assertFalse(res["updated"])
        self.assertEqual(res["reason"], "missing_index_data")

        row = self._asset_row(asset_id)
        self.assertEqual(row.get("last_update"), "2026-01-02")
        self.assertAlmostEqual(1000.0, float(row.get("current_value")), places=6)

    def test_pct_cdi_applies_across_year_boundary(self):
        asset_id = self._create_asset(
            symbol="RF_CDI_YEAR",
            rentability_type="PCT_CDI",
            index_name="CDI",
            index_pct=100.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2025-12-31",
        )
        self._insert_index_rate(index_name="CDI", ref_date="2026-01-02", value=0.10)

        res = invest_rentability.update_investment_value(asset_id, as_of_date="2026-01-02", user_id=self.uid)
        self.assertTrue(res["ok"])
        self.assertTrue(res["updated"])
        self.assertEqual(res["last_update"], "2026-01-02")
        self.assertEqual(res["processed_steps"], 1)

        expected = (Decimal("1000.0") * invest_rentability._factor_from_rate(Decimal("0.00100000"))).quantize(
            invest_rentability._CURRENT_Q,
            rounding=ROUND_HALF_UP,
        )
        self.assertAlmostEqual(float(expected), float(res["current_value"]), places=6)

    def test_ipca_spread_applies_ipca_month_end_and_spread_business_day(self):
        asset_id = self._create_asset(
            symbol="RF_IPCA",
            rentability_type="IPCA_SPREAD",
            index_name="IPCA",
            spread_rate=6.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2026-01-30",
        )
        self._insert_index_rate(index_name="IPCA", ref_date="2026-01-31", value=0.5)

        res = invest_rentability.update_investment_value(asset_id, as_of_date="2026-02-02", user_id=self.uid)
        self.assertTrue(res["ok"])
        self.assertTrue(res["updated"])
        self.assertEqual(res["last_update"], "2026-02-02")

        spread_daily = invest_rentability._annual_pct_to_daily_rate(Decimal("6.0"))
        expected = Decimal("1000.0")
        expected *= invest_rentability._factor_from_rate(Decimal("0.00500000"))  # IPCA Jan no fechamento
        expected *= invest_rentability._factor_from_rate(spread_daily)  # 2026-02-02 (dia útil)
        expected = expected.quantize(invest_rentability._CURRENT_Q, rounding=ROUND_HALF_UP)
        self.assertAlmostEqual(float(expected), float(res["current_value"]), places=6)

    def test_last_update_null_uses_first_buy_trade_date(self):
        asset_id = self._create_asset(
            symbol="RF_BASE_TRADE",
            rentability_type="PREFIXADO",
            fixed_rate=10.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update=None,
            created_at="2026-01-01",
        )
        self._insert_trade(asset_id=asset_id, date="2026-01-09", side="BUY", quantity=1.0, price=1000.0)

        res = invest_rentability.update_investment_value(asset_id, as_of_date="2026-01-12", user_id=self.uid)
        self.assertTrue(res["ok"])
        self.assertTrue(res["updated"])
        self.assertEqual(res["last_update"], "2026-01-12")
        self.assertEqual(res["processed_steps"], 1)

    def test_update_fixed_income_assets_only_auto_skips_manual(self):
        auto_id = self._create_asset(
            symbol="RF_AUTO_UPD",
            rentability_type="PCT_CDI",
            index_name="CDI",
            index_pct=100.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2026-01-02",
        )
        manual_id = self._create_asset(
            symbol="RF_MANUAL_SKIP",
            rentability_type="MANUAL",
            principal_amount=500.0,
            current_value=500.0,
            last_update="2026-01-02",
        )
        self._insert_index_rate(index_name="CDI", ref_date="2026-01-05", value=0.10)

        out = invest_rentability.update_fixed_income_assets(
            as_of_date="2026-01-05",
            user_id=self.uid,
            only_auto=True,
        )
        self.assertTrue(out["ok"])
        self.assertEqual(1, out["total_assets"])
        self.assertEqual(1, out["updated"])

        auto_row = self._asset_row(auto_id)
        manual_row = self._asset_row(manual_id)
        self.assertEqual("2026-01-05", auto_row.get("last_update"))
        self.assertEqual("2026-01-02", manual_row.get("last_update"))

    def test_update_fixed_income_assets_reset_from_principal(self):
        asset_id = self._create_asset(
            symbol="RF_RESET",
            rentability_type="PCT_CDI",
            index_name="CDI",
            index_pct=100.0,
            principal_amount=1000.0,
            current_value=1500.0,
            last_update="2026-01-31",
        )
        self._insert_trade(asset_id=asset_id, date="2026-01-01", side="BUY", quantity=1.0, price=1000.0)
        self._insert_index_rate(index_name="CDI", ref_date="2026-02-02", value=0.10)

        out = invest_rentability.update_fixed_income_assets(
            as_of_date="2026-02-02",
            user_id=self.uid,
            only_auto=True,
            reset_from_principal=True,
            asset_ids=[asset_id],
        )
        self.assertTrue(out["ok"])
        self.assertEqual(1, out["total_assets"])
        self.assertEqual(1, out["updated"])
        row = self._asset_row(asset_id)
        self.assertEqual("2026-02-02", row.get("last_update"))
        expected = (Decimal("1000.0") * invest_rentability._factor_from_rate(Decimal("0.00100000"))).quantize(
            invest_rentability._CURRENT_Q,
            rounding=ROUND_HALF_UP,
        )
        self.assertAlmostEqual(float(expected), float(row.get("current_value")), places=6)

    def test_preview_divergence_report_detects_pending_delta(self):
        asset_id = self._create_asset(
            symbol="RF_DIVERGE",
            rentability_type="PCT_CDI",
            index_name="CDI",
            index_pct=100.0,
            principal_amount=1000.0,
            current_value=1000.0,
            last_update="2026-01-02",
        )
        self._insert_index_rate(index_name="CDI", ref_date="2026-01-05", value=0.10)

        report = invest_rentability.preview_divergence_report(
            as_of_date="2026-01-05",
            user_id=self.uid,
            only_auto=True,
            threshold_pct=0.01,
        )
        self.assertTrue(report["ok"])
        self.assertGreaterEqual(report["total_rows"], 1)
        row = next((r for r in report["rows"] if int(r.get("asset_id", 0)) == asset_id), None)
        self.assertIsNotNone(row)
        self.assertGreater(abs(float(row["delta_pct"])), 0.01)


class ApiRentabilityValidationTests(unittest.TestCase):
    def _assert_http_400(self, fn, expected_fragment: str):
        with self.assertRaises(HTTPException) as ctx:
            fn()
        self.assertEqual(400, int(ctx.exception.status_code))
        self.assertIn(expected_fragment, str(ctx.exception.detail))

    def test_prefixado_requires_fixed_rate(self):
        self._assert_http_400(
            lambda: _validate_asset_rentability(
                asset_class="Renda Fixa",
                rentability_type="PREFIXADO",
                index_name=None,
                index_pct=None,
                spread_rate=None,
                fixed_rate=None,
            ),
            "PREFIXADO exige fixed_rate",
        )

    def test_pct_cdi_requires_index_name_cdi(self):
        self._assert_http_400(
            lambda: _validate_asset_rentability(
                asset_class="Renda Fixa",
                rentability_type="PCT_CDI",
                index_name="SELIC",
                index_pct=100.0,
                spread_rate=None,
                fixed_rate=None,
            ),
            "PCT_CDI exige index_name=CDI",
        )

    def test_ipca_spread_requires_spread_rate(self):
        self._assert_http_400(
            lambda: _validate_asset_rentability(
                asset_class="Tesouro Direto",
                rentability_type="IPCA_SPREAD",
                index_name="IPCA",
                index_pct=None,
                spread_rate=None,
                fixed_rate=None,
            ),
            "IPCA_SPREAD exige spread_rate",
        )

    def test_manual_rejects_extra_rate_fields(self):
        self._assert_http_400(
            lambda: _validate_asset_rentability(
                asset_class="Renda Fixa",
                rentability_type="MANUAL",
                index_name="CDI",
                index_pct=100.0,
                spread_rate=None,
                fixed_rate=None,
            ),
            "MANUAL não permite",
        )

    def test_non_fixed_income_rejects_auto_rentability(self):
        self._assert_http_400(
            lambda: _validate_asset_rentability(
                asset_class="Ações BR",
                rentability_type="PCT_CDI",
                index_name="CDI",
                index_pct=100.0,
                spread_rate=None,
                fixed_rate=None,
            ),
            "apenas para Renda Fixa",
        )

    def test_valid_combinations_return_normalized_payload(self):
        cdi = _validate_asset_rentability(
            asset_class="Renda Fixa",
            rentability_type="PCT_CDI",
            index_name="DI",
            index_pct=110.0,
            spread_rate=2.0,
            fixed_rate=None,
        )
        self.assertEqual("PCT_CDI", cdi["rentability_type"])
        self.assertEqual("CDI", cdi["index_name"])
        self.assertEqual(110.0, cdi["index_pct"])
        self.assertEqual(2.0, cdi["spread_rate"])
        self.assertIsNone(cdi["fixed_rate"])

        manual = _validate_asset_rentability(
            asset_class="Renda Fixa",
            rentability_type="MANUAL",
            index_name=None,
            index_pct=None,
            spread_rate=None,
            fixed_rate=None,
        )
        self.assertEqual("MANUAL", manual["rentability_type"])
        self.assertIsNone(manual["index_name"])
        self.assertIsNone(manual["index_pct"])
        self.assertIsNone(manual["spread_rate"])
        self.assertIsNone(manual["fixed_rate"])


if __name__ == "__main__":
    unittest.main()
