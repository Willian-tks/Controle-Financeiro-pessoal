import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import db as db_module
from api.main import app
from api.security import create_token


class MultiWorkspacePermissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._db_path = Path(cls._tmpdir.name) / "finance_test_multiworkspace.db"
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
        cls._tmpdir.cleanup()

    def setUp(self):
        with db_module.get_conn() as conn:
            tables = [
                "permissions",
                "workspace_users",
                "workspaces",
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
                INSERT INTO users(id, email, password_hash, display_name, role, global_role, is_active)
                VALUES
                    (1, 'owner@example.com', 'x', 'Owner', 'user', 'USER', 1),
                    (2, 'guest@example.com', 'x', 'Guest', 'user', 'USER', 1),
                    (3, 'other@example.com', 'x', 'Other', 'user', 'USER', 1),
                    (9, 'admin@example.com', 'x', 'Admin', 'admin', 'SUPER_ADMIN', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO workspaces(id, name, owner_user_id, status)
                VALUES
                    (101, 'WS Owner', 1, 'active'),
                    (102, 'WS Other', 3, 'active')
                """
            )
            conn.execute(
                """
                INSERT INTO workspace_users(workspace_id, user_id, role, created_by)
                VALUES
                    (101, 1, 'OWNER', 1),
                    (102, 3, 'OWNER', 3)
                """
            )

    def _headers(
        self,
        user_id: int,
        email: str,
        workspace_id: int,
        workspace_role: str = "GUEST",
        global_role: str = "USER",
    ) -> dict[str, str]:
        token = create_token(
            user_id=user_id,
            email=email,
            workspace_id=workspace_id,
            global_role=global_role,
            workspace_role=workspace_role,
        )
        return {"Authorization": f"Bearer {token}"}

    def _workspace_user_id(self, workspace_id: int, user_id: int) -> int:
        with db_module.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM workspace_users WHERE workspace_id = ? AND user_id = ?",
                (int(workspace_id), int(user_id)),
            ).fetchone()
            self.assertIsNotNone(row)
            return int(row["id"])

    def test_owner_can_add_guest_and_seed_default_permissions(self):
        headers = self._headers(1, "owner@example.com", 101, workspace_role="OWNER")
        resp = self.client.post(
            "/workspaces/members",
            json={"email": "guest@example.com", "role": "GUEST"},
            headers=headers,
        )
        self.assertEqual(200, resp.status_code, resp.text)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["created"])
        self.assertEqual("GUEST", str(data["member"]["workspace_role"]).upper())
        self.assertGreaterEqual(len(data["member"]["permissions"]), 5)

        list_resp = self.client.get("/workspaces/members", headers=headers)
        self.assertEqual(200, list_resp.status_code, list_resp.text)
        members = list_resp.json()
        guest_rows = [m for m in members if int(m.get("user_id", 0)) == 2]
        self.assertEqual(1, len(guest_rows))
        self.assertEqual("GUEST", str(guest_rows[0]["workspace_role"]).upper())

    def test_guest_cannot_access_users_module(self):
        with db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO workspace_users(workspace_id, user_id, role, created_by) VALUES (?, ?, 'GUEST', ?)",
                (101, 2, 1),
            )
        headers = self._headers(2, "guest@example.com", 101, workspace_role="GUEST")
        resp = self.client.get("/workspaces/members", headers=headers)
        self.assertEqual(403, resp.status_code)

    def test_owner_updates_guest_permissions_and_guest_can_add_account(self):
        with db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO workspace_users(workspace_id, user_id, role, created_by) VALUES (?, ?, 'GUEST', ?)",
                (101, 2, 1),
            )
        wsu_id = self._workspace_user_id(101, 2)
        with db_module.get_conn() as conn:
            # Sem can_add em contas.
            conn.execute(
                """
                INSERT INTO permissions(workspace_user_id, module, can_view, can_add, can_edit, can_delete)
                VALUES (?, 'contas', 1, 0, 0, 0)
                """,
                (wsu_id,),
            )

        guest_headers = self._headers(2, "guest@example.com", 101, workspace_role="GUEST")
        owner_headers = self._headers(1, "owner@example.com", 101, workspace_role="OWNER")

        denied = self.client.post(
            "/accounts",
            json={"name": "Conta G", "type": "Banco", "currency": "BRL", "show_on_dashboard": False},
            headers=guest_headers,
        )
        self.assertEqual(403, denied.status_code)

        update = self.client.put(
            "/workspaces/members/2/permissions",
            json={
                "permissions": [
                    {
                        "module": "contas",
                        "can_view": True,
                        "can_add": True,
                        "can_edit": False,
                        "can_delete": False,
                    }
                ]
            },
            headers=owner_headers,
        )
        self.assertEqual(200, update.status_code, update.text)

        allowed = self.client.post(
            "/accounts",
            json={"name": "Conta G", "type": "Banco", "currency": "BRL", "show_on_dashboard": False},
            headers=guest_headers,
        )
        self.assertEqual(200, allowed.status_code, allowed.text)
        self.assertTrue(allowed.json().get("ok"))

    def test_cross_workspace_access_is_blocked(self):
        with db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO workspace_users(workspace_id, user_id, role, created_by) VALUES (?, ?, 'GUEST', ?)",
                (102, 2, 3),
            )
        wsu_id = self._workspace_user_id(102, 2)
        with db_module.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO permissions(workspace_user_id, module, can_view, can_add, can_edit, can_delete)
                VALUES (?, 'contas', 1, 1, 1, 1)
                """,
                (wsu_id,),
            )

        # Usuário 2 não é membro do workspace 101.
        bad_headers = self._headers(2, "guest@example.com", 101, workspace_role="GUEST")
        resp = self.client.get("/accounts", headers=bad_headers)
        self.assertEqual(403, resp.status_code)

    def test_blocked_workspace_denies_owner_but_allows_super_admin(self):
        with db_module.get_conn() as conn:
            conn.execute("UPDATE workspaces SET status = 'blocked' WHERE id = 101")

        owner_headers = self._headers(1, "owner@example.com", 101, workspace_role="OWNER", global_role="USER")
        owner_resp = self.client.get("/accounts", headers=owner_headers)
        self.assertEqual(403, owner_resp.status_code)

        super_headers = self._headers(
            9,
            "admin@example.com",
            101,
            workspace_role="SUPER_ADMIN",
            global_role="SUPER_ADMIN",
        )
        super_resp = self.client.get("/accounts", headers=super_headers)
        self.assertEqual(200, super_resp.status_code, super_resp.text)

    def test_super_admin_can_create_and_block_workspace(self):
        super_headers = self._headers(
            9,
            "admin@example.com",
            101,
            workspace_role="SUPER_ADMIN",
            global_role="SUPER_ADMIN",
        )

        created_resp = self.client.post(
            "/admin/workspaces",
            json={"workspace_name": "WS Novo", "owner_email": "other@example.com"},
            headers=super_headers,
        )
        self.assertEqual(200, created_resp.status_code, created_resp.text)
        ws = created_resp.json().get("workspace") or {}
        ws_id = int(ws.get("workspace_id") or 0)
        self.assertGreater(ws_id, 0)

        list_resp = self.client.get("/admin/workspaces", headers=super_headers)
        self.assertEqual(200, list_resp.status_code, list_resp.text)
        ids = [int(item.get("workspace_id") or 0) for item in list_resp.json()]
        self.assertIn(ws_id, ids)

        block_resp = self.client.put(
            f"/admin/workspaces/{ws_id}/status",
            json={"status": "blocked"},
            headers=super_headers,
        )
        self.assertEqual(200, block_resp.status_code, block_resp.text)
        self.assertEqual("blocked", str(block_resp.json()["workspace"].get("workspace_status")))

        owner_headers = self._headers(1, "owner@example.com", 101, workspace_role="OWNER", global_role="USER")
        forbidden_resp = self.client.get("/admin/workspaces", headers=owner_headers)
        self.assertEqual(403, forbidden_resp.status_code)


if __name__ == "__main__":
    unittest.main()
