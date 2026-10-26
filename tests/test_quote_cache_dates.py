import unittest
from unittest.mock import Mock, patch

import invest_quotes as quotes


class BrapiDateTests(unittest.TestCase):
    def fetch(self, timestamp, price=10):
        response = Mock(status_code=200)
        response.json.return_value = {"results": [{"regularMarketPrice": price, "regularMarketTime": timestamp}]}
        with patch.object(quotes, "_get_brapi_token", return_value="test"), patch.object(quotes.requests, "get", return_value=response):
            return quotes.fetch_last_price_brapi("PETR4")

    def test_missing_invalid_and_future_date_are_not_replaced_with_today(self):
        for timestamp in (None, "", "invalid", 0, -1, True, "2999-01-01", "2024-02-30"):
            with self.subTest(timestamp=timestamp):
                result = self.fetch(timestamp)
                self.assertIsNone(result[0])
                self.assertIsNone(result[1])
                self.assertEqual(result[3].code, "invalid_data")

    def test_timestamp_uses_brazil_market_date_not_server_timezone(self):
        for timestamp in (1704155400, "2024-01-02T01:50:00Z", "2024-01-01T22:50:00-03:00"):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(self.fetch(timestamp), (10, "2024-01-01", "brapi", None))

    def test_explicit_day_is_preserved(self):
        self.assertEqual(self.fetch("2024-01-02"), (10, "2024-01-02", "brapi", None))

    def test_invalid_price_is_rejected_before_numeric_coercion(self):
        for price in (True, -1, 0, "NaN", float("inf")):
            with self.subTest(price=price):
                result = self.fetch("2024-01-02", price)
                self.assertIsNone(result[0])
                self.assertEqual(result[3].code, "invalid_data")

    def test_undated_brapi_uses_existing_alternative(self):
        error = quotes.QuoteFailure("missing date", "invalid_data", "brapi")
        with patch.object(quotes, "_get_brapi_token", return_value="test"), patch.object(quotes, "fetch_last_price_brapi", return_value=(None, None, None, error)), patch.object(quotes, "fetch_last_price_yf", return_value=(12, "2024-01-02", "yfinance")):
            self.assertEqual(quotes.fetch_last_price("PETR4", "Ações BR", "BRL"), (12, "2024-01-02", "yfinance", None))


class QuoteCacheTests(unittest.TestCase):
    asset = {"id": 1, "symbol": "PETR4", "asset_class": "Ações BR", "currency": "BRL"}

    def setUp(self):
        with quotes._QUOTE_CACHE_LOCK:
            quotes._QUOTE_CACHE.clear()
        self.env = patch.dict(quotes.os.environ, {"QUOTE_CACHE_TTL_S": "1800", "QUOTE_ERROR_CACHE_TTL_S": "60"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def tearDown(self):
        with quotes._QUOTE_CACHE_LOCK:
            quotes._QUOTE_CACHE.clear()

    def row(self, ok=True):
        return {"asset_id": 1, "symbol": "PETR4", "currency": "BRL", "ok": ok,
                "price": 10 if ok else None, "px_date": "2024-01-02" if ok else None,
                "src": "brapi" if ok else None, "error_code": None if ok else "rate_limited"}

    def test_hit_preserves_reference_date_and_remaps_asset_id(self):
        with patch.object(quotes.time, "monotonic", return_value=100) as clock, patch.object(quotes, "_fetch_one_asset_uncached", return_value=self.row()) as fetch:
            first = quotes._fetch_one_asset(self.asset, 3)
            clock.return_value = 130
            second = quotes._fetch_one_asset({**self.asset, "id": 99}, 3)
            self.assertFalse(first["cache_hit"])
            self.assertTrue(second["cache_hit"])
            self.assertEqual(second["asset_id"], 99)
            self.assertEqual(second["px_date"], "2024-01-02")
            self.assertEqual(second["fetched_at"], first["fetched_at"])
            self.assertEqual(fetch.call_count, 1)

    def test_expiration_and_currency_are_separate(self):
        with patch.object(quotes.time, "monotonic", return_value=100) as clock, patch.object(quotes, "_fetch_one_asset_uncached", side_effect=lambda *args: self.row()) as fetch:
            quotes._fetch_one_asset(self.asset, 3)
            quotes._fetch_one_asset({**self.asset, "currency": "USD"}, 3)
            clock.return_value = 1901
            self.assertFalse(quotes._fetch_one_asset(self.asset, 3)["cache_hit"])
            self.assertEqual(fetch.call_count, 3)

    def test_failed_cache_never_becomes_success_and_retry_recovers(self):
        with patch.object(quotes.time, "monotonic", return_value=100) as clock, patch.object(quotes, "_fetch_one_asset_uncached", side_effect=[self.row(False), self.row(True)]) as fetch:
            quotes._fetch_one_asset(self.asset, 3)
            clock.return_value = 120
            failed = quotes._fetch_one_asset(self.asset, 3)
            self.assertFalse(failed["ok"])
            self.assertTrue(failed["cache_hit"])
            self.assertEqual(failed["error_code"], "rate_limited")
            clock.return_value = 161
            self.assertTrue(quotes._fetch_one_asset(self.asset, 3)["ok"])
            self.assertEqual(fetch.call_count, 2)

    def test_cache_size_is_bounded(self):
        with patch.object(quotes, "_QUOTE_CACHE_MAX_ITEMS", 3), patch.object(quotes, "_fetch_one_asset_uncached", side_effect=lambda *args: self.row()):
            for index in range(5):
                quotes._fetch_one_asset({**self.asset, "symbol": f"TEST{index}"}, 3)
            self.assertEqual(len(quotes._QUOTE_CACHE), 3)


if __name__ == "__main__":
    unittest.main()
