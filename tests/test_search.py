import pytest
import json
import pandas as pd
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.search import search_transactions, search_json


class TestSearch:
    """Тесты для модуля поиска"""

    @pytest.fixture
    def sample_transactions(self):
        """Фикстура с тестовыми транзакциями"""
        return pd.DataFrame({
            'date': pd.to_datetime(['2024-01-15', '2024-01-14', '2024-01-13']),
            'amount': [-1000, -500, 200],
            'category': ['Супермаркеты', 'Кафе', 'Пополнение'],
            'description': ['Магнит', 'Starbucks', 'Перевод с карты'],
            'card_number': ['1234567890123456', '9876543210987654', '']
        })

    def test_search_by_category(self, sample_transactions):
        """Тест поиска по категории"""
        results = search_transactions("Супермаркеты", sample_transactions)
        assert len(results) == 1
        assert results[0]['category'] == 'Супермаркеты'
        assert results[0]['description'] == 'Магнит'

    def test_search_by_description(self, sample_transactions):
        """Тест поиска по описанию"""
        results = search_transactions("Starbucks", sample_transactions)
        assert len(results) == 1
        assert results[0]['description'] == 'Starbucks'
        assert results[0]['amount'] == 500

    def test_search_case_insensitive(self, sample_transactions):
        """Тест регистронезависимого поиска"""
        results = search_transactions("супермаркеты", sample_transactions)
        assert len(results) == 1

    def test_search_partial_match(self, sample_transactions):
        """Тест поиска по части слова"""
        results = search_transactions("Маг", sample_transactions)
        assert len(results) == 1
        assert results[0]['description'] == 'Магнит'

    def test_search_no_results(self, sample_transactions):
        """Тест поиска без результатов"""
        results = search_transactions("Несуществующее", sample_transactions)
        assert len(results) == 0

    def test_search_empty_query(self, sample_transactions):
        """Тест с пустым поисковым запросом"""
        results = search_transactions("", sample_transactions)
        assert len(results) == 0

    def test_search_income_transaction(self, sample_transactions):
        """Тест поиска доходной транзакции"""
        results = search_transactions("Перевод", sample_transactions)
        assert len(results) == 1
        assert results[0]['amount_type'] == 'income'
        assert results[0]['amount'] == 200

    def test_search_expense_transaction(self, sample_transactions):
        """Тест поиска расходной транзакции"""
        results = search_transactions("Кафе", sample_transactions)
        assert len(results) == 1
        assert results[0]['amount_type'] == 'expense'
        assert results[0]['amount'] == 500

    @patch('src.search.load_transactions')
    def test_search_json_success(self, mock_load, sample_transactions):
        """Тест успешного JSON-ответа"""
        mock_load.return_value = sample_transactions

        result = search_json("Супермаркеты")
        data = json.loads(result)

        assert data['query'] == "Супермаркеты"
        assert data['count'] == 1
        assert len(data['transactions']) == 1
        assert 'transactions' in data

    @patch('src.search.load_transactions')
    def test_search_json_no_results(self, mock_load, sample_transactions):
        """Тест JSON-ответа без результатов"""
        mock_load.return_value = sample_transactions

        result = search_json("Несуществующее")
        data = json.loads(result)

        assert data['query'] == "Несуществующее"
        assert data['count'] == 0
        assert data['transactions'] == []

    @patch('src.search.load_transactions')
    def test_search_json_with_error(self, mock_load):
        """Тест JSON-ответа при ошибке"""
        mock_load.side_effect = Exception("Test error")

        result = search_json("test")
        data = json.loads(result)

        assert data['query'] == "test"
        assert 'error' in data
        assert data['count'] == 0

    def test_search_transactions_without_dataframe(self):
        """Тест поиска без передачи DataFrame (должен загрузить из файла)"""
        with patch('src.search.load_transactions') as mock_load:
            mock_load.return_value = pd.DataFrame()
            results = search_transactions("test")
            assert results == []

    @pytest.mark.parametrize("search_query,expected_count", [
        ("Супермаркеты", 1),
        ("Кафе", 1),
        ("Перевод", 1),
        ("Магнит", 1),
        ("Starbucks", 1),
        ("xyz", 0),
    ])
    def test_search_parametrized(self, sample_transactions, search_query, expected_count):
        """Параметризованный тест поиска"""
        results = search_transactions(search_query, sample_transactions)
        assert len(results) == expected_count