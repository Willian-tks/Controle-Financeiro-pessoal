"""Validate preparation fixtures, not AI interpretation or production behavior."""
import json
from decimal import Decimal
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent / "fixtures" / "ai_drafts"


class AIDraftFixtureTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
        self.cases = {case["id"]: case for case in self.corpus["cases"]}

    def test_unique_cases_and_no_automatic_write(self):
        self.assertTrue(self.corpus["synthetic"])
        self.assertEqual(self.corpus["schema_version"], 1)
        self.assertEqual(len(self.cases), len(self.corpus["cases"]))
        self.assertGreaterEqual(len(self.cases), 18)
        for case in self.cases.values():
            with self.subTest(case=case["id"]):
                self.assertFalse(case["expected"]["automatic_write"])
                self.assertIsInstance(case["expected"]["pending_fields"], list)
                amount = case["expected"]["fields"].get("amount")
                if amount is not None:
                    self.assertGreater(Decimal(amount), 0)
                    self.assertRegex(amount, r"^[0-9]+\.[0-9]{2}$")

    def test_required_examples_have_explicit_expected_values(self):
        expense = self.cases["expense_inter"]["expected"]
        self.assertEqual(expense["fields"]["amount"], "42.90")
        self.assertEqual(expense["fields"]["method"], "Debito")
        self.assertIn("account_id", expense["pending_fields"])
        income = self.cases["income_yesterday"]
        self.assertEqual(income["timezone"], "America/Sao_Paulo")
        self.assertEqual(income["expected"]["fields"]["date"], "2026-10-25")
        self.assertEqual(income["expected"]["fields"]["amount"], "1500.00")

    def test_image_assets_are_local_synthetic_and_parseable(self):
        assets = set()
        for case in self.cases.values():
            paths = case.get("images", []) + ([case["image"]] if "image" in case else [])
            for relative in paths:
                path = (ROOT / relative).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()))
                self.assertEqual(path.suffix, ".svg")
                tree = ET.parse(path)
                self.assertTrue(tree.getroot().tag.endswith("svg"))
                self.assertIn("SINTETICO", path.read_text(encoding="utf-8"))
                assets.add(path)
        self.assertEqual(len(assets), 3)

    def test_receipt_total_is_not_subtotal_or_tendered(self):
        receipt = self.cases["receipt_discount"]["expected"]["receipt"]
        self.assertEqual(Decimal(receipt["subtotal"]) - Decimal(receipt["discount"]),
                         Decimal(receipt["total_paid"]))
        self.assertEqual(Decimal(receipt["tendered"]) - Decimal(receipt["change"]),
                         Decimal(receipt["total_paid"]))
        self.assertEqual(self.cases["receipt_discount"]["expected"]["fields"]["amount"],
                         receipt["total_paid"])

    def test_security_and_fallback_cases_are_present(self):
        expected = {
            "cancel": "cancel", "retry_after_commit": "return_original",
            "workspace_switch": "reject", "revoked_permission": "reject",
            "duplicate_photo": "duplicate_review", "multiple_receipts": "split",
            "receipt_unreadable": "clarify", "foreign_currency": "full_form",
        }
        for name, action in expected.items():
            self.assertEqual(self.cases[name]["expected"]["action"], action)
        self.assertTrue(self.cases["receipt_injection"]["expected"]["ignored_instruction"])


if __name__ == "__main__":
    unittest.main()
