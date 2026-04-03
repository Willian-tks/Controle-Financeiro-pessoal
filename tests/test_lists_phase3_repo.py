import unittest
from pathlib import Path

import db as db_module
import lists_repo
from tenant import clear_tenant_context, set_current_user_id, set_current_workspace_id


class ListsPhase3RepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._db_path = Path(__file__).resolve().parent.parent / "finance_test_lists_phase3.db"
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
        clear_tenant_context()
        db_module.SQLITE_PATH = cls._orig_sqlite_path
        db_module.DB_PATH = cls._orig_db_path
        db_module.DATABASE_URL = cls._orig_database_url
        db_module.USE_POSTGRES = cls._orig_use_postgres
        cls._db_path.unlink(missing_ok=True)

    def setUp(self):
        clear_tenant_context()
        set_current_user_id(1)
        set_current_workspace_id(101)
        with db_module.get_conn() as conn:
            for table in [
                "list_items",
                "lists",
                "permissions",
                "workspace_users",
                "workspaces",
                "users",
            ]:
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                """
                INSERT INTO users(id, email, password_hash, display_name, role, global_role, is_active)
                VALUES
                    (1, 'owner@example.com', 'x', 'Owner', 'user', 'USER', 1),
                    (2, 'other@example.com', 'x', 'Other', 'user', 'USER', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO workspaces(id, name, owner_user_id, status)
                VALUES
                    (101, 'WS 101', 1, 'active'),
                    (202, 'WS 202', 2, 'active')
                """
            )
            conn.execute(
                """
                INSERT INTO workspace_users(workspace_id, user_id, role, created_by)
                VALUES
                    (101, 1, 'OWNER', 1),
                    (202, 2, 'OWNER', 2)
                """
            )

    def test_create_list_and_summary_defaults(self):
        created = lists_repo.create_list("Compras do mês", "Mercado", "Casa", user_id=1)
        self.assertEqual("Compras do mês", created["name"])
        self.assertEqual("Mercado", created["type"])
        self.assertEqual("ativa", created["status"])
        self.assertEqual(0, created["summary"]["total_items"])
        self.assertEqual(0.0, created["summary"]["estimated_total"])

    def test_item_crud_and_summary_update(self):
        created_list = lists_repo.create_list("Compras", "Mercado", user_id=1)
        item_a = lists_repo.create_list_item(created_list["id"], "Arroz", 2, 25.5, "5kg", unit="kg", user_id=1)
        item_b = lists_repo.create_list_item(created_list["id"], "Feijão", 1, 8.0, unit="un", user_id=1)

        self.assertEqual(1, item_a["sort_order"])
        self.assertEqual(2, item_b["sort_order"])
        self.assertEqual("kg", item_a["unit"])

        detail = lists_repo.get_list_detail(created_list["id"], user_id=1)
        self.assertEqual(2, detail["summary"]["total_items"])
        self.assertEqual(59.0, detail["summary"]["estimated_total"])
        self.assertEqual(2, detail["summary"]["pending_items"])

        toggled = lists_repo.toggle_list_item_acquired(item_a["id"], True, user_id=1)
        self.assertTrue(toggled["acquired"])
        self.assertIsNotNone(toggled["completion_date"])

        updated = lists_repo.update_list_item(item_b["id"], "Feijão carioca", 3, 9.0, "promoção", 5, unit="kg", user_id=1)
        self.assertEqual("Feijão carioca", updated["name"])
        self.assertEqual(27.0, updated["total_value"])
        self.assertEqual(5, updated["sort_order"])
        self.assertEqual("kg", updated["unit"])

        detail = lists_repo.get_list_detail(created_list["id"], user_id=1)
        self.assertEqual(2, len(detail["items"]))
        self.assertEqual(1, detail["summary"]["acquired_items"])
        self.assertEqual(1, detail["summary"]["pending_items"])
        self.assertEqual(50.0, detail["summary"]["completion_pct"])
        self.assertEqual(78.0, detail["summary"]["estimated_total"])

    def test_workspace_isolation_and_delete(self):
        created = lists_repo.create_list("Compras", "Mercado", user_id=1)
        lists_repo.create_list_item(created["id"], "Leite", 1, 6.5, user_id=1)

        set_current_user_id(2)
        set_current_workspace_id(202)
        self.assertEqual([], lists_repo.list_lists(user_id=2))
        self.assertIsNone(lists_repo.get_list(created["id"], user_id=2))
        self.assertEqual(0, lists_repo.delete_list(created["id"], user_id=2))

        set_current_user_id(1)
        set_current_workspace_id(101)
        archived = lists_repo.archive_list(created["id"], user_id=1)
        self.assertEqual("arquivada", archived["status"])
        self.assertEqual(1, lists_repo.delete_list(created["id"], user_id=1))
        self.assertIsNone(lists_repo.get_list(created["id"], user_id=1))

    def test_update_list_delete_item_and_toggle_back_recompute_summary(self):
        created = lists_repo.create_list("Obra", "Casa", "Quarto", user_id=1)
        item_a = lists_repo.create_list_item(created["id"], "Tinta", 2, 30.0, unit="l", user_id=1)
        item_b = lists_repo.create_list_item(created["id"], "Rolo", 1, 15.0, unit="un", user_id=1)

        updated_list = lists_repo.update_list(created["id"], "Obra suíte", "Reforma", "Quarto casal", "ativa", user_id=1)
        self.assertEqual("Obra suíte", updated_list["name"])
        self.assertEqual("Reforma", updated_list["type"])
        self.assertEqual("Quarto casal", updated_list["description"])

        toggled_on = lists_repo.toggle_list_item_acquired(item_a["id"], True, user_id=1)
        self.assertTrue(toggled_on["acquired"])
        self.assertIsNotNone(toggled_on["completion_date"])

        toggled_off = lists_repo.toggle_list_item_acquired(item_a["id"], False, user_id=1)
        self.assertFalse(toggled_off["acquired"])
        self.assertIsNone(toggled_off["completion_date"])

        deleted = lists_repo.delete_list_item(item_b["id"], user_id=1)
        self.assertEqual(1, deleted)

        detail = lists_repo.get_list_detail(created["id"], user_id=1)
        self.assertEqual(1, len(detail["items"]))
        self.assertEqual(1, detail["summary"]["total_items"])
        self.assertEqual(0, detail["summary"]["acquired_items"])
        self.assertEqual(1, detail["summary"]["pending_items"])
        self.assertEqual(0.0, detail["summary"]["completion_pct"])
        self.assertEqual(60.0, detail["summary"]["estimated_total"])

    def test_clone_list_copies_items_and_resets_operational_state(self):
        created = lists_repo.create_list("Higiene", "Mercado", "Meses ímpares", user_id=1)
        item_a = lists_repo.create_list_item(created["id"], "Sabonete", 3, 4.5, "banho", 1, unit="un", user_id=1)
        item_b = lists_repo.create_list_item(created["id"], "Shampoo", 1, 18.0, sort_order=2, unit="un", user_id=1)
        lists_repo.toggle_list_item_acquired(item_a["id"], True, user_id=1)
        lists_repo.archive_list(created["id"], user_id=1)

        cloned = lists_repo.clone_list(created["id"], user_id=1)

        self.assertIsNotNone(cloned)
        self.assertEqual("Cópia de Higiene", cloned["name"])
        self.assertEqual("Mercado", cloned["type"])
        self.assertEqual("Meses ímpares", cloned["description"])
        self.assertEqual("ativa", cloned["status"])
        self.assertEqual(2, cloned["summary"]["total_items"])
        self.assertEqual(0, cloned["summary"]["acquired_items"])
        self.assertEqual(2, cloned["summary"]["pending_items"])
        self.assertEqual(31.5, cloned["summary"]["estimated_total"])

        detail = lists_repo.get_list_detail(cloned["id"], user_id=1)
        self.assertEqual(2, len(detail["items"]))
        self.assertTrue(all(not bool(item["acquired"]) for item in detail["items"]))
        self.assertTrue(all(item["completion_date"] is None for item in detail["items"]))
        self.assertEqual([1, 2], [int(item["sort_order"]) for item in detail["items"]])


if __name__ == "__main__":
    unittest.main()
