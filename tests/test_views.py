import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.views import main_page
from src.utils import (
    get_greeting,
    get_currency_rates,
    get_stock_prices,
)


class TestViews:
    """Тесты для модуля views.py"""

    @patch('src.views.load_transactions')
    @patch('src.views.get_currency_rates')
    @patch('src.views.get_stock_prices')
    def test_main_page_success(self, mock_stocks, mock_currency, mock_load):
        """Тест успешного формирования ответа"""
        mock_load.return_value = MagicMock()
        mock_load.return_value.empty = False
        mock_currency.return_value = [{'currency': 'USD', 'rate': 90.5}]
        mock_stocks.return_value = [{'stock': 'AAPL', 'price': 150.0}]

        result = main_page("2024-01-15 12:00:00")
        data = json.loads(result)

        assert 'greeting' in data
        assert 'cards' in data
        assert 'top_transactions' in data
        assert 'currency_rates' in data
        assert 'stock_prices' in data

    def test_main_page_with_invalid_date(self):
        """Тест с неверным форматом даты - должна использовать текущее время"""
        result = main_page("invalid-date")
        data = json.loads(result)

        assert 'greeting' in data
        assert 'cards' in data
        assert 'top_transactions' in data
        # При неверной дате функция использует текущее время и не возвращает ошибку
        assert 'error' not in data

    def test_main_page_without_param(self):
        """Тест без параметра"""
        result = main_page()
        data = json.loads(result)

        assert 'greeting' in data
        assert isinstance(data['greeting'], str)

    @patch('src.views.load_transactions')
    def test_main_page_empty_transactions(self, mock_load):
        """Тест с пустыми транзакциями"""
        mock_load.return_value = MagicMock()
        mock_load.return_value.empty = True

        result = main_page("2024-01-15 12:00:00")
        data = json.loads(result)

        assert data['cards'] == []
        assert data['top_transactions'] == []


class TestUtils:
    """Тесты для модуля utils.py"""

    @pytest.mark.parametrize("hour,expected", [
        (5, "Доброй ночи"),
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
    ])
    def test_get_greeting(self, hour, expected):
        """Тест приветствия в разное время"""
        current_time = datetime(2024, 1, 15, hour, 0, 0)
        assert get_greeting(current_time) == expected

    @patch('requests.get')
    def test_get_currency_rates_success(self, mock_get):
        """Тест успешного получения курсов валют"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'rates': {'USD': 90.5, 'EUR': 98.3}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = get_currency_rates(['USD', 'EUR'])
        assert len(result) == 2
        assert result[0]['currency'] == 'USD'

    def test_get_stock_prices(self):
        """Тест получения цен акций"""
        result = get_stock_prices(['AAPL', 'MSFT'])
        assert len(result) == 2
        assert result[0]['price'] > 0