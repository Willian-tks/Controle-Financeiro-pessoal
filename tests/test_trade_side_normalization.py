import unittest

from api.importers import _norm_trade_side as norm_side_csv
from api.main import _norm_trade_side as norm_side_api


class TradeSideNormalizationTests(unittest.TestCase):
    def test_api_accepts_buy_sell(self):
        self.assertEqual(norm_side_api("BUY"), "BUY")
        self.assertEqual(norm_side_api("sell"), "SELL")

    def test_api_accepts_business_terms(self):
        self.assertEqual(norm_side_api("APLICAÇÃO"), "BUY")
        self.assertEqual(norm_side_api("APLICACAO"), "BUY")
        self.assertEqual(norm_side_api("RESGATE"), "SELL")
        self.assertEqual(norm_side_api("compra"), "BUY")
        self.assertEqual(norm_side_api("venda"), "SELL")

    def test_api_accepts_short_forms(self):
        self.assertEqual(norm_side_api("C"), "BUY")
        self.assertEqual(norm_side_api("V"), "SELL")

    def test_api_rejects_unknown_values(self):
        self.assertEqual(norm_side_api(""), "")
        self.assertEqual(norm_side_api("HOLD"), "")

    def test_csv_normalization_matches_api(self):
        samples = [
            "BUY",
            "SELL",
            "APLICAÇÃO",
            "APLICACAO",
            "RESGATE",
            "COMPRA",
            "VENDA",
            "C",
            "V",
            "",
            "HOLD",
        ]
        for sample in samples:
            self.assertEqual(norm_side_csv(sample), norm_side_api(sample))


if __name__ == "__main__":
    unittest.main()
