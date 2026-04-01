import unittest
from pathlib import Path

import db as db_module


class ListsPhase1SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._db_path = Path(__file__).resolve().parent.parent / "finance_test_lists_phase1.db"
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

    def test_lists_tables_and_indexes_exist(self):
        with db_module.get_conn() as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('lists', 'list_items')"
                ).fetchall()
            }
            self.assertEqual({"lists", "list_items"}, tables)

            list_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(lists)").fetchall()
            }
            self.assertTrue(
                {
                    "id",
                    "workspace_id",
                    "name",
                    "type",
                    "description",
                    "status",
                    "created_at",
                    "updated_at",
                }.issubset(list_columns)
            )

            item_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(list_items)").fetchall()
            }
            self.assertTrue(
                {
                    "id",
                    "workspace_id",
                    "list_id",
                    "name",
                    "quantity",
                    "unit",
                    "suggested_value",
                    "total_value",
                    "acquired",
                    "completion_date",
                    "notes",
                    "sort_order",
                    "created_at",
                    "updated_at",
                }.issubset(item_columns)
            )

            indexes = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index' AND name LIKE 'idx_list%'"
                ).fetchall()
            }
            self.assertTrue(
                {
                    "idx_lists_workspace",
                    "idx_lists_workspace_status",
                    "idx_lists_workspace_type",
                    "idx_list_items_workspace",
                    "idx_list_items_workspace_list",
                }.issubset(indexes)
            )

    def test_lists_support_insert_and_read(self):
        with db_module.get_conn() as conn:
            conn.execute("DELETE FROM list_items")
            conn.execute("DELETE FROM lists")
            conn.execute(
                """
                INSERT INTO lists(workspace_id, name, type, description, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (101, "Compras do mês", "Mercado", "Lista base", "ativa"),
            )
            list_id = int(conn.execute("SELECT id FROM lists WHERE workspace_id = ?", (101,)).fetchone()["id"])
            conn.execute(
                """
                INSERT INTO list_items(
                    workspace_id, list_id, name, quantity, unit, suggested_value, total_value,
                    acquired, completion_date, notes, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (101, list_id, "Arroz", 2, "kg", 25.5, 51.0, 0, None, "Pacote de 5kg", 1),
            )

            row = conn.execute(
                """
                SELECT li.workspace_id, li.list_id, li.name, li.quantity, li.unit, li.suggested_value, li.total_value, l.status
                FROM list_items li
                JOIN lists l ON l.id = li.list_id
                WHERE li.workspace_id = ?
                """,
                (101,),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(101, int(row["workspace_id"]))
            self.assertEqual(list_id, int(row["list_id"]))
            self.assertEqual("Arroz", row["name"])
            self.assertEqual("kg", row["unit"])
            self.assertEqual("ativa", row["status"])


if __name__ == "__main__":
    unittest.main()
