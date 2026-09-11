import unittest
from unittest.mock import patch
from fastapi import HTTPException
from api.main import invest_create_trade
from api.schemas import TradeCreateRequest


class TradeCurrencyTests(unittest.TestCase):
    def run_trade(self, currency, asset_class, fx, side='BUY'):
        asset = dict(currency=currency, asset_class=asset_class, broker_account_id=2, symbol='SPY')
        body = TradeCreateRequest(asset_id=1, date='2026-08-17', side=side,
                                  quantity=0.64658795, price=773.29,
                                  exchange_rate=fx, fees=2, taxes=1)
        with patch('api.main.invest_repo.get_asset', return_value=asset), \
             patch('api.main.reports.account_balance_by_id', return_value=10000), \
             patch('api.main.repo.ensure_category', return_value=1), \
             patch('api.main.repo.insert_transaction') as cash, \
             patch('api.main.invest_repo.insert_trade') as trade:
            invest_create_trade(body, user={'id': 1})
            return cash.call_args.kwargs, trade.call_args.kwargs

    def test_usd_etf_and_stock_convert_cash_and_preserve_original_price(self):
        for cls in ('ETFs US', 'Stocks US'):
            for side in ('BUY', 'SELL'):
                with self.subTest(cls=cls, side=side):
                    cash, trade = self.run_trade('USD', cls, 5.2, side)
                    gross = 0.64658795 * 773.29
                    expected = -(gross + 3) * 5.2 if side == 'BUY' else (gross - 3) * 5.2
                    self.assertAlmostEqual(cash['amount'], expected)
                    self.assertEqual(trade['exchange_rate'], 5.2)
                    self.assertEqual(trade['price'], 773.29)

    def test_usd_etf_requires_exchange_rate(self):
        for fx in (None, 0, -1):
            with self.subTest(fx=fx), self.assertRaises(HTTPException) as error:
                self.run_trade('USD', 'ETFs US', fx)
            self.assertEqual(error.exception.status_code, 400)

    def test_brl_etf_ignores_exchange_rate(self):
        cash, trade = self.run_trade('BRL', 'ETFs BR', 5.2)
        self.assertEqual(trade['exchange_rate'], 1)
        self.assertAlmostEqual(cash['amount'], -(0.64658795 * 773.29 + 3))
