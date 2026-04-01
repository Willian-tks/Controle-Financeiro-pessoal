import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import db as db_module
from api.main import app
from api.security import create_token


class ListsPhase4ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._db_path = Path(__file__).resolve().parent.parent / "finance_test_lists_phase4.db"
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
        cls.client = TestClient(app)

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
                    (101, 'WS Owner', 1, 'active'),
                    (202, 'WS Other', 2, 'active')
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

    def _headers(self, user_id: int, email: str, workspace_id: int, workspace_role: str = "OWNER") -> dict[str, str]:
        token = create_token(
            user_id=user_id,
            email=email,
            workspace_id=workspace_id,
            global_role="USER",
            workspace_role=workspace_role,
        )
        return {"Authorization": f"Bearer {token}"}

    def test_lists_endpoints_crud_and_toggle(self):
        headers = self._headers(1, "owner@example.com", 101)

        create_resp = self.client.post(
            "/lists",
            headers=headers,
            json={"name": "Compras do mês", "type": "Mercado", "description": "Casa", "status": "ativa"},
        )
        self.assertEqual(200, create_resp.status_code, create_resp.text)
        created = create_resp.json()
        self.assertEqual("Compras do mês", created["name"])
        self.assertEqual(0, created["summary"]["total_items"])
        list_id = int(created["id"])

        item_resp = self.client.post(
            f"/lists/{list_id}/items",
            headers=headers,
            json={"name": "Arroz", "quantity": 2, "unit": "kg", "suggested_value": 10.5, "notes": "5kg"},
        )
        self.assertEqual(200, item_resp.status_code, item_resp.text)
        item = item_resp.json()
        self.assertEqual(21.0, item["total_value"])
        self.assertEqual("kg", item["unit"])
        item_id = int(item["id"])

        toggle_resp = self.client.patch(
            f"/items/{item_id}/toggle-acquired",
            headers=headers,
            json={"acquired": True},
        )
        self.assertEqual(200, toggle_resp.status_code, toggle_resp.text)
        toggled = toggle_resp.json()
        self.assertTrue(toggled["acquired"])
        self.assertTrue(toggled["completion_date"])

        detail_resp = self.client.get(f"/lists/{list_id}", headers=headers)
        self.assertEqual(200, detail_resp.status_code, detail_resp.text)
        detail = detail_resp.json()
        self.assertEqual(1, detail["summary"]["total_items"])
        self.assertEqual(1, detail["summary"]["acquired_items"])
        self.assertEqual(0, detail["summary"]["pending_items"])
        self.assertEqual(100.0, detail["summary"]["completion_pct"])
        self.assertEqual(21.0, detail["summary"]["estimated_total"])
        self.assertEqual(1, len(detail["items"]))

        archive_resp = self.client.patch(f"/lists/{list_id}/archive", headers=headers)
        self.assertEqual(200, archive_resp.status_code, archive_resp.text)
        self.assertEqual("arquivada", archive_resp.json()["status"])

    def test_lists_are_isolated_by_workspace(self):
        owner_headers = self._headers(1, "owner@example.com", 101)
        other_headers = self._headers(2, "other@example.com", 202)

        create_resp = self.client.post(
            "/lists",
            headers=owner_headers,
            json={"name": "Compras", "type": "Mercado", "status": "ativa"},
        )
        self.assertEqual(200, create_resp.status_code, create_resp.text)
        list_id = int(create_resp.json()["id"])

        list_resp = self.client.get("/lists", headers=other_headers)
        self.assertEqual(200, list_resp.status_code, list_resp.text)
        self.assertEqual([], list_resp.json())

        get_resp = self.client.get(f"/lists/{list_id}", headers=other_headers)
        self.assertEqual(404, get_resp.status_code, get_resp.text)

        delete_resp = self.client.delete(f"/lists/{list_id}", headers=other_headers)
        self.assertEqual(404, delete_resp.status_code, delete_resp.text)

    def test_update_and_delete_endpoints_for_list_and_item(self):
        headers = self._headers(1, "owner@example.com", 101)

        create_resp = self.client.post(
            "/lists",
            headers=headers,
            json={"name": "Casa nova", "type": "Mudança", "description": "Pendências"},
        )
        self.assertEqual(200, create_resp.status_code, create_resp.text)
        list_id = int(create_resp.json()["id"])

        update_resp = self.client.put(
            f"/lists/{list_id}",
            headers=headers,
            json={"name": "Casa nova 2026", "type": "Mudança", "description": "Pendências gerais", "status": "ativa"},
        )
        self.assertEqual(200, update_resp.status_code, update_resp.text)
        updated_list = update_resp.json()
        self.assertEqual("Casa nova 2026", updated_list["name"])
        self.assertEqual("Pendências gerais", updated_list["description"])

        item_resp = self.client.post(
            f"/lists/{list_id}/items",
            headers=headers,
            json={"name": "Caixa organizadora", "quantity": 3, "unit": "un", "suggested_value": 12.0, "notes": "Sala"},
        )
        self.assertEqual(200, item_resp.status_code, item_resp.text)
        item_id = int(item_resp.json()["id"])

        item_update_resp = self.client.put(
            f"/items/{item_id}",
            headers=headers,
            json={"name": "Caixa organizadora grande", "quantity": 4, "unit": "kg", "suggested_value": 15.0, "notes": "Sala principal", "sort_order": 7},
        )
        self.assertEqual(200, item_update_resp.status_code, item_update_resp.text)
        updated_item = item_update_resp.json()
        self.assertEqual("Caixa organizadora grande", updated_item["name"])
        self.assertEqual(60.0, updated_item["total_value"])
        self.assertEqual(7, updated_item["sort_order"])
        self.assertEqual("kg", updated_item["unit"])

        item_delete_resp = self.client.delete(f"/items/{item_id}", headers=headers)
        self.assertEqual(200, item_delete_resp.status_code, item_delete_resp.text)
        self.assertTrue(item_delete_resp.json()["ok"])

        detail_resp = self.client.get(f"/lists/{list_id}", headers=headers)
        self.assertEqual(200, detail_resp.status_code, detail_resp.text)
        detail = detail_resp.json()
        self.assertEqual(0, detail["summary"]["total_items"])
        self.assertEqual([], detail["items"])

        list_delete_resp = self.client.delete(f"/lists/{list_id}", headers=headers)
        self.assertEqual(200, list_delete_resp.status_code, list_delete_resp.text)
        self.assertTrue(list_delete_resp.json()["ok"])

        missing_resp = self.client.get(f"/lists/{list_id}", headers=headers)
        self.assertEqual(404, missing_resp.status_code, missing_resp.text)

    def test_validation_errors_for_invalid_list_and_item_payloads(self):
        headers = self._headers(1, "owner@example.com", 101)

        invalid_list_resp = self.client.post(
            "/lists",
            headers=headers,
            json={"name": "   ", "type": "Mercado", "status": "ativa"},
        )
        self.assertEqual(422, invalid_list_resp.status_code, invalid_list_resp.text)

        invalid_status_resp = self.client.post(
            "/lists",
            headers=headers,
            json={"name": "Compras", "type": "Mercado", "status": "fechada"},
        )
        self.assertEqual(422, invalid_status_resp.status_code, invalid_status_resp.text)

        create_resp = self.client.post(
            "/lists",
            headers=headers,
            json={"name": "Compras válidas", "type": "Mercado", "status": "ativa"},
        )
        self.assertEqual(200, create_resp.status_code, create_resp.text)
        list_id = int(create_resp.json()["id"])

        invalid_qty_resp = self.client.post(
            f"/lists/{list_id}/items",
            headers=headers,
            json={"name": "Arroz", "quantity": 0, "suggested_value": 10.0},
        )
        self.assertEqual(422, invalid_qty_resp.status_code, invalid_qty_resp.text)

        invalid_value_resp = self.client.post(
            f"/lists/{list_id}/items",
            headers=headers,
            json={"name": "Feijão", "quantity": 1, "suggested_value": -1},
        )
        self.assertEqual(422, invalid_value_resp.status_code, invalid_value_resp.text)

        invalid_unit_resp = self.client.post(
            f"/lists/{list_id}/items",
            headers=headers,
            json={"name": "Leite", "quantity": 1, "unit": "caixa", "suggested_value": 8},
        )
        self.assertEqual(422, invalid_unit_resp.status_code, invalid_unit_resp.text)


if __name__ == "__main__":
    unittest.main()
