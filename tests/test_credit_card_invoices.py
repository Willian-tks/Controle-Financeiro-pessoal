import unittest
from datetime import date, timedelta
from pathlib import Path

import db as db_module
import repo
import reports


class CreditCardInvoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._db_path = Path(__file__).resolve().parent.parent / "finance_test_cards.db"
        cls._db_path.unlink(missing_ok=True)
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
        cls._db_path.unlink(missing_ok=True)

    def setUp(self):
        with db_module.get_conn() as conn:
            for table in [
                "credit_card_charges",
                "credit_card_invoices",
                "credit_cards",
                "transactions",
                "categories",
                "accounts",
                "invites",
                "users",
            ]:
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                """
                INSERT INTO users(id, email, password_hash, display_name, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (1, "cards@example.com", "x", "Cards", "user", 1),
            )
            conn.execute(
                "INSERT INTO accounts(id, name, type, currency, show_on_dashboard, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (10, "Santander SX", "Cartao", "BRL", 0, 1),
            )
            conn.execute(
                "INSERT INTO accounts(id, name, type, currency, show_on_dashboard, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (11, "Santander Conta", "Banco", "BRL", 1, 1),
            )
            conn.execute(
                "INSERT INTO categories(id, name, kind, user_id) VALUES (?, ?, ?, ?)",
                (20, "Serviços", "Despesa", 1),
            )

    def test_register_credit_charge_uses_default_close_day_for_legacy_cards(self):
        repo.create_credit_card(
            "Santander SX",
            "Mastercard",
            "Vermelho",
            "Credito",
            10,
            11,
            17,
            None,
            user_id=1,
        )
        card_id = int(repo.list_credit_cards(user_id=1)[0]["id"])

        repo.register_credit_charge(
            card_id=card_id,
            purchase_date="2026-03-01",
            amount=100.0,
            category_id=20,
            description="Teste legado",
            user_id=1,
        )

        rows = repo.list_credit_card_invoices(user_id=1, card_id=card_id)
        self.assertEqual(1, len(rows))
        self.assertEqual("2026-03", rows[0]["invoice_period"])
        self.assertEqual("2026-03-17", rows[0]["due_date"])
        self.assertAlmostEqual(100.0, float(rows[0]["total_amount"]))

    def test_invoice_listing_and_payment_use_charge_totals_when_invoice_row_is_stale(self):
        repo.create_credit_card(
            "Santander SX",
            "Mastercard",
            "Vermelho",
            "Credito",
            10,
            11,
            17,
            12,
            user_id=1,
        )
        card_id = int(repo.list_credit_cards(user_id=1)[0]["id"])

        repo.register_credit_charge(
            card_id=card_id,
            purchase_date="2026-03-01",
            amount=242.90,
            category_id=20,
            description="Cerato (1/10)",
            user_id=1,
        )
        repo.register_credit_charge(
            card_id=card_id,
            purchase_date="2026-03-05",
            amount=77.10,
            category_id=20,
            description="Seguro Casa (1/10)",
            user_id=1,
        )

        with db_module.get_conn() as conn:
            conn.execute(
                "UPDATE credit_card_invoices SET total_amount = ?, paid_amount = 0, status = 'OPEN' WHERE card_id = ? AND invoice_period = ?",
                (242.90, card_id, "2026-03"),
            )

        rows = repo.list_credit_card_invoices(user_id=1, status="OPEN", card_id=card_id)
        self.assertEqual(1, len(rows))
        self.assertAlmostEqual(320.0, float(rows[0]["total_amount"]), places=2)
        self.assertAlmostEqual(0.0, float(rows[0]["paid_amount"]), places=2)

        out = repo.pay_credit_card_invoice(int(rows[0]["id"]), "2026-03-17", user_id=1)
        self.assertAlmostEqual(320.0, float(out["paid_amount"]), places=2)

        with db_module.get_conn() as conn:
            tx = conn.execute(
                "SELECT amount_brl FROM transactions WHERE description LIKE ?",
                ("PGTO FATURA Santander SX (2026-03)%",),
            ).fetchone()
            inv = conn.execute(
                "SELECT paid_amount, status FROM credit_card_invoices WHERE id = ?",
                (int(rows[0]["id"]),),
            ).fetchone()
            charges = conn.execute(
                "SELECT COUNT(*) AS qty FROM credit_card_charges WHERE card_id = ? AND invoice_period = ? AND paid = 1",
                (card_id, "2026-03"),
            ).fetchone()

        self.assertIsNotNone(tx)
        self.assertAlmostEqual(-320.0, float(tx["amount_brl"]), places=2)
        self.assertAlmostEqual(320.0, float(inv["paid_amount"]), places=2)
        self.assertEqual("PAID", str(inv["status"]))
        self.assertEqual(2, int(charges["qty"]))

    def test_update_credit_card_due_day_refreshes_open_invoice_due_date(self):
        repo.create_credit_card(
            "Inter Black",
            "Mastercard",
            "Black",
            "Credito",
            10,
            11,
            5,
            3,
            user_id=1,
        )
        card_id = int(repo.list_credit_cards(user_id=1)[0]["id"])
        repo.register_credit_charge(
            card_id=card_id,
            purchase_date="2026-03-01",
            amount=170.89,
            category_id=20,
            description="Compra teste",
            user_id=1,
        )

        before = repo.list_credit_card_invoices(user_id=1, status="OPEN", card_id=card_id)
        self.assertEqual("2026-03-05", before[0]["due_date"])

        repo.update_credit_card(
            card_id=card_id,
            name="Inter Black",
            brand="Mastercard",
            model="Black",
            card_type="Credito",
            card_account_id=10,
            source_account_id=11,
            due_day=10,
            close_day=5,
            user_id=1,
        )

        after = repo.list_credit_card_invoices(user_id=1, status="OPEN", card_id=card_id)
        self.assertEqual(1, len(after))
        self.assertEqual("2026-03", after[0]["invoice_period"])
        self.assertEqual("2026-03-10", after[0]["due_date"])
        self.assertAlmostEqual(170.89, float(after[0]["total_amount"]), places=2)

    def test_commitments_summary_groups_next_seven_days(self):
        today = date.today()
        today_iso = today.isoformat()
        day_two_iso = (today + timedelta(days=2)).isoformat()
        outside_week_iso = (today + timedelta(days=8)).isoformat()
        overdue_iso = (today - timedelta(days=1)).isoformat()

        with db_module.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO transactions(id, date, description, amount_brl, account_id, category_id, method, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (100, today_iso, "Hoje", -100.0, 11, 20, "Futuro", 1),
            )
            conn.execute(
                """
                INSERT INTO transactions(id, date, description, amount_brl, account_id, category_id, method, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (101, day_two_iso, "Depois", -55.5, 11, 20, "Agendado", 1),
            )
            conn.execute(
                """
                INSERT INTO transactions(id, date, description, amount_brl, account_id, category_id, method, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (102, outside_week_iso, "Fora da semana", -80.0, 11, 20, "Futuro", 1),
            )
            conn.execute(
                """
                INSERT INTO transactions(id, date, description, amount_brl, account_id, category_id, method, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (103, overdue_iso, "Vencido", -30.0, 11, 20, "Futuro", 1),
            )

        out = reports.commitments_summary(user_id=1)
        week = out["week"]

        self.assertEqual(7, len(week))
        self.assertEqual(today_iso, week[0]["date"])
        self.assertAlmostEqual(100.0, float(week[0]["total"]), places=2)
        self.assertAlmostEqual(0.0, float(week[1]["total"]), places=2)
        self.assertAlmostEqual(55.5, float(week[2]["total"]), places=2)
        self.assertAlmostEqual(235.5, float(out["a_vencer"]), places=2)
        self.assertAlmostEqual(30.0, float(out["vencidos"]), places=2)
