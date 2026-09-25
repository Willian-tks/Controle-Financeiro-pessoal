import unittest
from unittest.mock import patch, Mock
import invest_quotes as q

class YahooChartTests(unittest.TestCase):
    def fetch(self, row):
        response = Mock(status_code=200)
        response.json.return_value = {'chart': {'result': [row], 'error': None}}
        with patch.object(q.requests, 'get', return_value=response) as get:
            result = q.fetch_last_price_yahoo_http('AAL')
            self.assertIn('/v8/finance/chart/AAL', get.call_args.args[0])
            return result

    def test_market_price_keeps_reference_date(self):
        result = self.fetch({'meta': {'regularMarketPrice': 12.5, 'regularMarketTime': 1704155400, 'gmtoffset': -18000}})
        self.assertEqual(result, (12.5, '2024-01-01', 'yahoo_chart', None))

    def test_invalid_market_price_uses_last_valid_close(self):
        for invalid in (None, 0, -1, float('nan'), float('inf'), True):
            with self.subTest(invalid=invalid):
                row = {'meta': {'regularMarketPrice': invalid}, 'timestamp': [1704155400, 1704241800], 'indicators': {'quote': [{'close': [10.5, None]}]}}
                self.assertEqual(self.fetch(row)[:2], (10.5, '2024-01-02'))

    def test_price_without_date_is_rejected(self):
        self.assertIsNone(self.fetch({'meta': {'regularMarketPrice': 12.5}})[0])

    def test_http_failure_uses_stooq(self):
        with patch.object(q.requests, 'get', return_value=Mock(status_code=401)), patch.object(q, 'fetch_last_price_stooq_us', return_value=(12., '2024-01-02', 'stooq', None)):
            self.assertEqual(q.fetch_last_price('AAL', 'Stocks US', 'USD'), (12., '2024-01-02', 'stooq', None))

    def test_both_errors_are_reported(self):
        with patch.object(q.requests, 'get', return_value=Mock(status_code=401)), patch.object(q, 'fetch_last_price_stooq_us', return_value=(None, None, None, 'Stooq HTTP 503')):
            result = q.fetch_last_price('AAL', 'Stocks US', 'USD')
            self.assertIsNone(result[0])
            self.assertIn('401', result[3])
            self.assertIn('503', result[3])

    def test_empty_provider_response(self):
        response = Mock(status_code=200)
        response.json.return_value = {'chart': {'result': None, 'error': {'code': 'Not Found'}}}
        with patch.object(q.requests, 'get', return_value=response):
            self.assertIsNone(q.fetch_last_price_yahoo_http('AAL')[0])

if __name__ == '__main__':
    unittest.main()
