import pytest
import json

from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.search import simple_search, simple_search_json, load_transactions_from_excel


class TestSimpleSearch:
    """Тесты для функции простого поиска"""

    @pytest.fixture
    def sample_transactions(self):
        """Фикстура с тестовыми транзакциями"""
        return [
            {
                "date": "15.01.2024",
                "amount": -1000,
                "amount_abs": 1000,
                "amount_type": "expense",
                "category": "Супермаркеты",
                "description": "Магнит",
                "card_last_digits": "3456"
            },
            {
                "date": "14.01.2024",
                "amount": -500,
                "amount_abs": 500,
                "amount_type": "expense",
                "category": "Кафе",
                "description": "Starbucks",
                "card_last_digits": "7654"
            },
            {
                "date": "13.01.2024",
                "amount": 200,
                "amount_abs": 200,
                "amount_type": "income",
                "category": "Пополнение",
                "description": "Перевод с карты",
                "card_last_digits": ""
            }
        ]

    def test_search_by_category(self, sample_transactions):
        """Тест поиска по категории"""
        results = simple_search(sample_transactions, "Супермаркеты")
        assert len(results) == 1
        assert results[0]['category'] == "Супермаркеты"
        assert results[0]['description'] == "Магнит"

    def test_search_by_description(self, sample_transactions):
        """Тест поиска по описанию"""
        results = simple_search(sample_transactions, "Starbucks")
        assert len(results) == 1
        assert results[0]['description'] == "Starbucks"
        assert results[0]['amount'] == 500

    def test_search_case_insensitive(self, sample_transactions):
        """Тест регистронезависимого поиска"""
        results = simple_search(sample_transactions, "супермаркеты")
        assert len(results) == 1

    def test_search_partial_match(self, sample_transactions):
        """Тест поиска по части слова"""
        results = simple_search(sample_transactions, "Маг")
        assert len(results) == 1
        assert results[0]['description'] == "Магнит"

    def test_search_no_results(self, sample_transactions):
        """Тест поиска без результатов"""
        results = simple_search(sample_transactions, "Несуществующее")
        assert len(results) == 0

    def test_search_empty_query(self, sample_transactions):
        """Тест с пустым поисковым запросом"""
        results = simple_search(sample_transactions, "")
        assert len(results) == 0

    def test_search_empty_transactions(self):
        """Тест с пустым списком транзакций"""
        results = simple_search([], "test")
        assert len(results) == 0

    def test_search_none_query(self, sample_transactions):
        """Тест с None в качестве запроса"""
        results = simple_search(sample_transactions, None)  # type: ignore
        assert len(results) == 0

    def test_search_income_transaction(self, sample_transactions):
        """Тест поиска доходной транзакции"""
        results = simple_search(sample_transactions, "Перевод")
        assert len(results) == 1
        assert results[0]['amount_type'] == "income"
        assert results[0]['amount'] == 200

    @pytest.mark.parametrize("search_query,expected_count", [
        ("Супермаркеты", 1),
        ("Кафе", 1),
        ("Перевод", 1),
        ("Магнит", 1),
        ("Starbucks", 1),
        ("xyz", 0),
        ("", 0),
    ])
    def test_search_parametrized(self, sample_transactions, search_query, expected_count):
        """Параметризованный тест поиска"""
        results = simple_search(sample_transactions, search_query)
        assert len(results) == expected_count


class TestSimpleSearchJSON:
    """Тесты для JSON-функции поиска"""

    @pytest.fixture
    def sample_transactions(self):
        return [
            {
                "date": "15.01.2024",
                "amount": -1000,
                "amount_abs": 1000,
                "amount_type": "expense",
                "category": "Супермаркеты",
                "description": "Магнит",
                "card_last_digits": "3456"
            }
        ]

    def test_simple_search_json_success(self, sample_transactions):
        """Тест успешного JSON-ответа"""
        result = simple_search_json(sample_transactions, "Супермаркеты", save_to_file=False)
        data = json.loads(result)

        assert data['query'] == "Супермаркеты"
        assert data['count'] == 1
        assert len(data['transactions']) == 1
        assert 'transactions' in data

    def test_simple_search_json_no_results(self, sample_transactions):
        """Тест JSON-ответа без результатов"""
        result = simple_search_json(sample_transactions, "Несуществующее", save_to_file=False)
        data = json.loads(result)

        assert data['query'] == "Несуществующее"
        assert data['count'] == 0
        assert data['transactions'] == []

    def test_simple_search_json_empty_query(self, sample_transactions):
        """Тест JSON-ответа с пустым запросом"""
        result = simple_search_json(sample_transactions, "", save_to_file=False)
        data = json.loads(result)

        assert data['query'] == ""
        assert data['count'] == 0
        assert data['transactions'] == []

    def test_simple_search_json_none_query(self, sample_transactions):
        """Тест JSON-ответа с None в качестве запроса"""
        result = simple_search_json(sample_transactions, None, save_to_file=False)  # type: ignore
        data = json.loads(result)

        assert data['count'] == 0
        assert data['transactions'] == []

    def test_simple_search_json_empty_transactions(self):
        """Тест JSON-ответа с пустым списком транзакций"""
        result = simple_search_json([], "test", save_to_file=False)
        data = json.loads(result)

        assert data['query'] == "test"
        assert data['count'] == 0
        assert data['transactions'] == []

class TestLoadTransactionsFromExcel:
    """Тесты для загрузки транзакций из Excel"""

    @patch('pandas.read_excel')
    def test_load_transactions_success(self, mock_read_excel):
        """Тест успешной загрузки транзакций"""
        # Создаём мок для DataFrame
        mock_df = MagicMock()
        mock_df.columns = ['Дата операции', 'Сумма операции', 'Категория', 'Описание']

        # Создаём мок для строки
        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda x: {
            'Дата операции': '15.01.2024 10:30:00',
            'Сумма операции': -1000,
            'Категория': 'Супермаркеты',
            'Описание': 'Магнит'
        }.get(x, '')

        # Настраиваем iterrows
        mock_df.iterrows.return_value = [(0, mock_row)]
        mock_read_excel.return_value = mock_df

        result = load_transactions_from_excel("dummy.xlsx")

        assert isinstance(result, list)
        assert len(result) == 1

    @patch('pandas.read_excel')
    def test_load_transactions_file_not_found(self, mock_read_excel):
        """Тест обработки ошибки при отсутствии файла"""
        mock_read_excel.side_effect = FileNotFoundError("File not found")

        result = load_transactions_from_excel("nonexistent.xlsx")

        assert result == []

    @patch('pandas.read_excel')
    def test_load_transactions_permission_error(self, mock_read_excel):
        """Тест обработки ошибки доступа к файлу"""
        mock_read_excel.side_effect = PermissionError("Permission denied")

        result = load_transactions_from_excel("protected.xlsx")

        assert result == []

    @patch('pandas.read_excel')
    def test_load_transactions_empty_file(self, mock_read_excel):
        """Тест обработки пустого файла"""
        from pandas.errors import EmptyDataError
        mock_read_excel.side_effect = EmptyDataError("No columns to parse")

        result = load_transactions_from_excel("empty.xlsx")

        assert result == []

    @patch('pandas.read_excel')
    def test_load_transactions_invalid_format(self, mock_read_excel):
        """Тест обработки неверного формата данных"""
        # Создаём мок для DataFrame с неверными данными
        mock_df = MagicMock()
        mock_df.columns = ['Дата операции', 'Сумма операции']

        mock_row = MagicMock()
        mock_row.__getitem__.side_effect = lambda x: {
            'Дата операции': None,
            'Сумма операции': None
        }.get(x)

        mock_df.iterrows.return_value = [(0, mock_row)]
        mock_read_excel.return_value = mock_df

        result = load_transactions_from_excel("invalid.xlsx")

        # Должен вернуть список с транзакцией, где значения по умолчанию
        assert isinstance(result, list)
        assert len(result) == 1