import unittest
from unittest.mock import Mock, patch

import requests
import invest_quotes as quotes


class QuoteFailureTests(unittest.TestCase):
    def test_http_status_is_structured_without_echoing_response(self):
        for status, code in ((429, "rate_limited"), (401, "access_denied"), (403, "access_denied"), (404, "no_data"), (503, "provider_error")):
            with self.subTest(status=status), patch.object(quotes, "_get_brapi_token", return_value="private-token"), patch.object(quotes.requests, "get", return_value=Mock(status_code=status, text="private-token")):
                error = quotes.fetch_last_price_brapi("PETR4")[3]
                self.assertIsInstance(error, str)
                self.assertEqual(error.code, code)
                self.assertEqual(error.http_status, status)
                self.assertNotIn("private-token", error)

    def test_empty_results_are_not_a_provider_outage(self):
        response = Mock(status_code=200)
        response.json.return_value = {"results": []}
        with patch.object(quotes, "_get_brapi_token", return_value="test"), patch.object(quotes.requests, "get", return_value=response):
            self.assertEqual(quotes.fetch_last_price_brapi("PETR4")[3].code, "no_data")

    def test_timeout_does_not_expose_request_details(self):
        with patch.object(quotes, "_get_brapi_token", return_value="test"), patch.object(quotes.requests, "get", side_effect=requests.Timeout("url?token=private-token")):
            error = quotes.fetch_last_price_brapi("PETR4")[3]
            self.assertEqual(error.code, "timeout")
            self.assertNotIn("private-token", error)

    def test_fallback_keeps_both_provider_failures(self):
        first = quotes.QuoteFailure("Yahoo HTTP 429", "rate_limited", "yahoo_chart", 429)
        second = quotes.QuoteFailure("Stooq sem dados", "no_data", "stooq")
        with patch.object(quotes, "fetch_last_price_yahoo_http", return_value=(None, None, None, first)), patch.object(quotes, "fetch_last_price_stooq_us", return_value=(None, None, None, second)):
            error = quotes.fetch_last_price("AAL", "Stocks US", "USD")[3]
            self.assertEqual(error.code, "rate_limited")
            self.assertEqual([item["provider"] for item in error.attempts], ["yahoo_chart", "stooq"])

    def test_successful_fallback_does_not_keep_an_error(self):
        with patch.object(quotes, "fetch_last_price_yahoo_http", return_value=(None, None, None, quotes.QuoteFailure("limit", "rate_limited", "yahoo_chart"))), patch.object(quotes, "fetch_last_price_stooq_us", return_value=(12, "2024-01-02", "stooq", None)):
            self.assertEqual(quotes.fetch_last_price("AAL", "Stocks US", "USD"), (12, "2024-01-02", "stooq", None))

    def test_report_preserves_structured_failure_and_currency(self):
        error = quotes.QuoteFailure("limited", "rate_limited", "brapi", 429)
        with patch.object(quotes, "_call_with_timeout", return_value=(True, (None, None, None, error), None)):
            row = quotes._fetch_one_asset_uncached({"id": 1, "symbol": "PETR4", "currency": "BRL"}, 3)
        self.assertFalse(row["ok"])
        self.assertEqual(row["error_code"], "rate_limited")
        self.assertEqual(row["currency"], "BRL")
        self.assertEqual(row["attempts"][0]["http_status"], 429)

    def test_invalid_values_are_never_successful(self):
        for price, day in ((0, "2024-01-02"), (-1, "2024-01-02"), (float("nan"), "2024-01-02"), (float("inf"), "2024-01-02"), (True, "2024-01-02"), (10, "not-a-date"), (10, "2024-02-30")):
            with self.subTest(price=price, day=day), patch.object(quotes, "_call_with_timeout", return_value=(True, (price, day, "test", None), None)):
                row = quotes._fetch_one_asset_uncached({"id": 1, "symbol": "TEST", "currency": "USD"}, 3)
                self.assertFalse(row["ok"])
                self.assertEqual(row["error_code"], "invalid_data")


if __name__ == "__main__":
    unittest.main()
