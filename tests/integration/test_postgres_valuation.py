"""Run only against the disposable CI database, never the production DATABASE_URL."""
import os
from pathlib import Path
import sys
import unittest
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_invest_valuation import ValuationContract
import db


@unittest.skipUnless(os.getenv("DOMUS_POSTGRES_TEST_URL"), "Disposable PostgreSQL not configured")
class PostgresValuationTests(ValuationContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = os.environ["DOMUS_POSTGRES_TEST_URL"]
        parsed = urlparse(url)
        if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.path != "/domus_ci_test":
            raise RuntimeError("Tests require local disposable database domus_ci_test.")
        cls.original = db.DATABASE_URL, db.USE_POSTGRES
        db.DATABASE_URL, db.USE_POSTGRES = url, True
        try:
            db.init_db()
        except Exception:
            db.DATABASE_URL, db.USE_POSTGRES = cls.original
            raise

    @classmethod
    def tearDownClass(cls):
        db.DATABASE_URL, db.USE_POSTGRES = cls.original
