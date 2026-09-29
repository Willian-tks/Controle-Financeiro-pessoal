import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

import db
import invest_reports
import invest_repo
from api.main import invest_create_position_adjustment, _prepare_position_adjustment
from api.schemas import PositionAdjustmentCreateRequest


class PositionAdjustmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).resolve().parent.parent / "data" / f"finance_test_adjustments_{next(tempfile._get_candidate_names())}.db"
        cls.original = (db.SQLITE_PATH, db.DB_PATH, db.DATABASE_URL, db.USE_POSTGRES)
        db.DATABASE_URL = ""
        db.USE_POSTGRES = False
        db.SQLITE_PATH = cls.path
        db.DB_PATH = cls.path
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        db.SQLITE_PATH, db.DB_PATH, db.DATABASE_URL, db.USE_POSTGRES = cls.original
        if cls.path.exists():
            cls.path.unlink()

    def setUp(self):
        with db.get_conn() as conn:
            for table in ("trades", "assets", "transactions", "users"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                "INSERT INTO users(id, email, password_hash, display_name, role, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (1, "adjust@example.com", "x", "Adjust", "user", 1),
            )
            self.brl_asset = int(conn.execute(
                "INSERT INTO assets(symbol, name, asset_class, sector, currency, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("TEST3", "Teste", "Ações BR", "Teste", "BRL", 1),
            ).lastrowid)
            self.usd_asset = int(conn.execute(
                "INSERT INTO assets(symbol, name, asset_class, sector, currency, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("TEST", "Test", "Stocks US", "Test", "USD", 1),
            ).lastrowid)
            conn.execute(
                "INSERT INTO trades(asset_id, date, side, quantity, price, exchange_rate, fees, taxes, user_id) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)",
                (self.brl_asset, "2026-01-01", "BUY", 10, 20, 1, 1),
            )

    def body(self, **overrides):
        data = dict(asset_id=self.brl_asset, date="2026-09-29", direction="INCREASE", quantity=5,
                    unit_cost=30, adjustment_type="MANUAL", reason="Conciliação da custódia")
        data.update(overrides)
        return PositionAdjustmentCreateRequest(**data)

    def test_increase_changes_quantity_and_cost_without_cash(self):
        result = invest_create_position_adjustment(self.body(), user={"id": 1})
        self.assertEqual(10, result["before"]["quantity"])
        self.assertEqual(15, result["after"]["quantity"])
        self.assertEqual(350, result["after"]["cost_basis"])
        with db.get_conn() as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
            row = dict(conn.execute("SELECT * FROM trades WHERE id = ?", (result["adjustment_id"],)).fetchone())
        self.assertEqual("ADJUST_IN", row["side"])
        self.assertEqual("MANUAL", row["operation_type"])
        self.assertEqual("Conciliação da custódia", row["reason"])
        self.assertEqual(1, row["created_by_user_id"])

    def test_decrease_uses_average_cost_and_does_not_realize_result(self):
        result = invest_create_position_adjustment(self.body(direction="DECREASE", quantity=4, unit_cost=None), user={"id": 1})
        self.assertEqual(6, result["after"]["quantity"])
        self.assertEqual(120, result["after"]["cost_basis"])
        pos = invest_reports.positions_avg_cost(invest_reports.df_trades(user_id=1)).iloc[0]
        self.assertEqual(0, pos["realized_pnl"])
        self.assertEqual(20, pos["avg_cost"])

    def test_bonus_allows_zero_cost_but_manual_does_not(self):
        bonus = invest_create_position_adjustment(
            self.body(adjustment_type="BONUS", unit_cost=0, reason="Bonificação informada pela corretora"),
            user={"id": 1},
        )
        self.assertEqual(200, bonus["after"]["cost_basis"])
        with self.assertRaises(HTTPException):
            _prepare_position_adjustment(self.body(unit_cost=0), user_id=1)

    def test_usd_requires_fx_and_converts_cost(self):
        with self.assertRaises(HTTPException):
            _prepare_position_adjustment(self.body(asset_id=self.usd_asset), user_id=1)
        result = invest_create_position_adjustment(
            self.body(asset_id=self.usd_asset, quantity=2, unit_cost=10, exchange_rate=5), user={"id": 1}
        )
        self.assertEqual(100, result["after"]["cost_basis"])

    def test_reversal_is_traceable_and_restores_position(self):
        created = invest_create_position_adjustment(self.body(), user={"id": 1})
        ok, message, reversal_id = invest_repo.reverse_position_adjustment(created["adjustment_id"], user_id=1)
        self.assertTrue(ok, message)
        self.assertIsNotNone(reversal_id)
        pos = invest_reports.positions_avg_cost(invest_reports.df_trades(user_id=1)).iloc[0]
        self.assertEqual(10, pos["qty"])
        self.assertEqual(200, pos["cost_basis"])
        with db.get_conn() as conn:
            reversal = dict(conn.execute("SELECT * FROM trades WHERE id = ?", (reversal_id,)).fetchone())
        self.assertEqual("REVERSAL", reversal["operation_type"])
        self.assertEqual(created["adjustment_id"], reversal["reversed_trade_id"])
        self.assertFalse(invest_repo.reverse_position_adjustment(created["adjustment_id"], user_id=1)[0])


if __name__ == "__main__":
    unittest.main()
