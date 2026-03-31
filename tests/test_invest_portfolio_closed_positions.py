import tempfile
import unittest
from pathlib import Path

from api.main import _prepare_fixed_income_trade
import db as db_module
import invest_reports


class ClosedFixedIncomePositionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = None
        cls._db_path = Path(__file__).resolve().parent.parent / "data" / f"finance_test_closed_positions_{next(tempfile._get_candidate_names())}.db"
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
        try:
            if cls._db_path.exists():
                cls._db_path.unlink()
        except Exception:
            pass

    def setUp(self):
        with db_module.get_conn() as conn:
            tables = [
                "asset_prices",
                "prices",
                "income_events",
                "trades",
                "assets",
                "transactions",
                "categories",
                "accounts",
                "users",
            ]
            for table in tables:
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                """
                INSERT INTO users(id, email, password_hash, display_name, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "test@example.com", "x", "Test", "user", 1),
            )
        self.uid = 1

    def test_closed_fixed_income_does_not_keep_current_value_in_market_value(self):
        with db_module.get_conn() as conn:
            asset_id = int(
                conn.execute(
                    """
                    INSERT INTO assets(
                        symbol, name, asset_class, sector, currency,
                        rentability_type, principal_amount, current_value, last_update, user_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "CDB_INTER",
                        "CDB Inter",
                        "Renda Fixa",
                        "Não definido",
                        "BRL",
                        "MANUAL",
                        20000.0,
                        23372.05,
                        "2026-03-30",
                        self.uid,
                    ),
                ).lastrowid
            )
            conn.execute(
                """
                INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, note, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (asset_id, "2026-03-01", "BUY", 1.0, 20000.0, 1.0, 0.0, 0.0, None, self.uid),
            )
            conn.execute(
                """
                INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, note, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (asset_id, "2026-03-30", "SELL", 1.0, 23372.05, 1.0, 0.0, 0.0, None, self.uid),
            )

        pos, _, _ = invest_reports.portfolio_view(user_id=self.uid)
        self.assertEqual(1, len(pos))
        row = pos.iloc[0]
        self.assertAlmostEqual(0.0, float(row["qty"]), places=6)
        self.assertAlmostEqual(0.0, float(row["cost_basis"]), places=6)
        self.assertAlmostEqual(0.0, float(row["market_value"]), places=6)
        self.assertAlmostEqual(3372.05, float(row["realized_pnl"]), places=6)

    def test_partial_fixed_income_sell_keeps_remaining_position(self):
        with db_module.get_conn() as conn:
            asset_id = int(
                conn.execute(
                    """
                    INSERT INTO assets(
                        symbol, name, asset_class, sector, currency,
                        rentability_type, principal_amount, current_value, last_update, user_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "CDB_INTER",
                        "CDB Inter",
                        "Renda Fixa",
                        "Não definido",
                        "BRL",
                        "PCT_CDI",
                        20000.0,
                        35916.40,
                        "2026-03-27",
                        self.uid,
                    ),
                ).lastrowid
            )
            conn.execute(
                """
                INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, note, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (asset_id, "2026-03-01", "BUY", 1.0, 20000.0, 1.0, 0.0, 0.0, None, self.uid),
            )
            asset = dict(conn.execute("SELECT * FROM assets WHERE id = ? AND user_id = ?", (asset_id, self.uid)).fetchone())

        prepared = _prepare_fixed_income_trade(
            asset=asset,
            side="SELL",
            quantity=1.0,
            price=23372.05,
            trade_date="2026-03-30",
            user_id=self.uid,
        )

        self.assertGreater(float(prepared["quantity"]), 0.0)
        self.assertLess(float(prepared["quantity"]), 1.0)
        self.assertAlmostEqual(23372.05, float(prepared["quantity"]) * float(prepared["price"]), places=4)
        self.assertAlmostEqual(12544.35, float(prepared["current_value"]), places=2)
        self.assertAlmostEqual(6985.30, float(prepared["principal_amount"]), places=2)
