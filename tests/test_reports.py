import pytest
import pandas as pd
from datetime import timedelta
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.reports import (
    load_transactions,
    filter_by_last_three_months,
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
)

# ==================== ФИКСТУРЫ ====================


@pytest.fixture
def sample_transactions_df():
    """Фикстура: создаёт тестовый DataFrame с транзакциями"""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2021-12-31 16:44:00",
                    "2021-12-30 10:30:00",
                    "2021-12-15 14:20:00",
                    "2021-11-20 09:15:00",
                    "2021-11-10 18:45:00",
                    "2021-10-15 12:00:00",
                    "2021-10-05 08:30:00",
                    "2021-09-15 20:00:00",  # Изменено с 2021-09-01 на 2021-09-15
                    "2021-08-15 11:00:00",
                ]
            ),
            "amount": [
                -500.0,
                -1200.0,
                -300.0,
                -800.0,
                -150.0,
                -2000.0,
                -50.0,
                -100.0,
                -50.0,
            ],
            "category": [
                "Супермаркеты",
                "Супермаркеты",
                "Фастфуд",
                "Супермаркеты",
                "Такси",
                "Супермаркеты",
                "Аптеки",
                "Супермаркеты",
                "Другое",
            ],
            "description": [
                "Колхоз",
                "Магнит",
                "McDonald's",
                "SPAR",
                "Яндекс Такси",
                "Перекрёсток",
                "Аптека",
                "Магнит",
                "Прочее",
            ],
            "currency": ["RUB"] * 9,
            "status": ["OK"] * 9,
        }
    )


@pytest.fixture
def empty_df():
    """Фикстура: пустой DataFrame"""
    return pd.DataFrame()


# ==================== ТЕСТЫ ДЛЯ filter_by_last_three_months ====================


class TestFilterByLastThreeMonths:
    """Тесты для фильтрации по последним 3 месяцам"""

    def test_filter_with_date_param(self, sample_transactions_df):
        """Тест фильтрации с указанием даты"""
        result = filter_by_last_three_months(sample_transactions_df, "2021-12-31")

        # Выведем все даты для отладки
        print(f"\nДаты в результате: {result['date'].tolist()}")

        # Проверяем, что результат не пустой
        assert len(result) > 0
        # Проверяем, что все даты в диапазоне
        assert result["date"].min() >= pd.Timestamp("2021-10-02")
        assert result["date"].max() <= pd.Timestamp("2021-12-31")

    def test_filter_without_date(self, sample_transactions_df):
        """Тест фильтрации без указания даты (используется максимальная дата)"""
        result = filter_by_last_three_months(sample_transactions_df)

        max_date = sample_transactions_df["date"].max()
        three_months_ago = max_date - timedelta(days=90)

        assert all(result["date"] >= three_months_ago)
        assert all(result["date"] <= max_date)
        assert len(result) > 0

    def test_filter_empty_dataframe(self, empty_df):
        """Тест фильтрации пустого DataFrame"""
        result = filter_by_last_three_months(empty_df, "2021-12-31")
        assert result.empty

    @pytest.mark.parametrize(
        "test_date,expected_min_count",
        [
            ("2021-12-31", 6),
            ("2021-11-30", 4),
            ("2021-10-31", 3),
            ("2021-09-30", 2),
            ("2021-01-01", 0),
        ],
    )
    def test_filter_parametrized(
        self, sample_transactions_df, test_date, expected_min_count
    ):
        """Параметризованный тест фильтрации с разными датами"""
        result = filter_by_last_three_months(sample_transactions_df, test_date)

        # Проверяем, что количество транзакций соответствует ожидаемому минимуму
        # (может быть больше, но не меньше)
        assert len(result) >= expected_min_count

        # Проверяем тип результата
        assert isinstance(result, pd.DataFrame)


# ==================== ТЕСТЫ ДЛЯ spending_by_category ====================


class TestSpendingByCategory:
    """Тесты для отчёта по категориям"""

    def test_spending_by_category_found(self, sample_transactions_df):
        """Тест поиска транзакций по существующей категории"""
        result = spending_by_category(
            sample_transactions_df, "Супермаркеты", "2021-12-31"
        )

        assert not result.empty
        # В диапазоне 90 дней от 2021-12-31 есть 3 транзакции с категорией 'Супермаркеты'
        assert len(result) == 3
        assert all(result["category"] == "Супермаркеты")

    def test_spending_by_category_not_found(self, sample_transactions_df):
        """Тест поиска по несуществующей категории"""
        result = spending_by_category(
            sample_transactions_df, "Несуществующая категория", "2021-12-31"
        )
        assert result.empty

    def test_spending_by_category_empty_df(self, empty_df):
        """Тест с пустым DataFrame"""
        result = spending_by_category(empty_df, "Супермаркеты", "2021-12-31")
        assert result.empty

    @pytest.mark.parametrize(
        "category,expected_count",
        [
            ("Супермаркеты", 3),
            ("Фастфуд", 1),
            ("Такси", 1),
            ("Аптеки", 1),
            ("Другое", 0),
        ],
    )
    def test_spending_by_category_parametrized(
        self, sample_transactions_df, category, expected_count
    ):
        """Параметризованный тест для разных категорий"""
        result = spending_by_category(sample_transactions_df, category, "2021-12-31")
        assert len(result) == expected_count


# ==================== ТЕСТЫ ДЛЯ spending_by_weekday ====================


class TestSpendingByWeekday:
    """Тесты для отчёта по дням недели"""

    def test_spending_by_weekday_empty_df(self, empty_df):
        """Тест с пустым DataFrame"""
        result = spending_by_weekday(empty_df, "2021-12-31")
        assert result.empty

    @pytest.mark.parametrize(
        "test_date",
        [
            "2021-12-31",
            "2021-11-30",
            "2021-10-31",
            None,
        ],
    )
    def test_spending_by_weekday_parametrized(self, sample_transactions_df, test_date):
        """Параметризованный тест для разных дат"""
        result = spending_by_weekday(sample_transactions_df, test_date)
        assert isinstance(result, pd.DataFrame)


# ==================== ТЕСТЫ ДЛЯ spending_by_workday ====================


class TestSpendingByWorkday:
    """Тесты для отчёта по рабочим/выходным дням"""

    def test_spending_by_workday_structure(self, sample_transactions_df):
        """Тест структуры результата отчёта по рабочим/выходным дням"""
        result = spending_by_workday(sample_transactions_df, "2021-12-31")

        assert not result.empty
        assert "day_type" in result.columns
        assert "average_spending" in result.columns
        assert "transaction_count" in result.columns
        assert "total_spending" in result.columns
        assert len(result) == 2

    def test_spending_by_workday_empty_df(self, empty_df):
        """Тест с пустым DataFrame"""
        result = spending_by_workday(empty_df, "2021-12-31")
        assert result.empty

    @pytest.mark.parametrize(
        "test_date",
        [
            "2021-12-31",
            "2021-11-30",
            None,
        ],
    )
    def test_spending_by_workday_parametrized(self, sample_transactions_df, test_date):
        """Параметризованный тест для разных дат"""
        result = spending_by_workday(sample_transactions_df, test_date)
        assert isinstance(result, pd.DataFrame)


# ==================== ТЕСТЫ ДЛЯ load_transactions (с моками) ====================


class TestLoadTransactions:
    """Тесты для функции загрузки транзакций"""

    @patch("pandas.read_excel")
    def test_load_transactions_success(self, mock_read_excel):
        """Тест успешной загрузки транзакций"""
        mock_read_excel.return_value = pd.DataFrame(
            {
                "Дата операции": ["31.12.2021 16:44:00"],
                "Сумма операции": [-500],
                "Категория": ["Супермаркеты"],
                "Описание": ["Колхоз"],
            }
        )

        result = load_transactions("dummy_path.xlsx")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "date" in result.columns
        assert "amount" in result.columns

    @patch("pandas.read_excel")
    def test_load_transactions_file_not_found(self, mock_read_excel):
        """Тест обработки ошибки при отсутствии файла"""
        mock_read_excel.side_effect = FileNotFoundError("File not found")

        result = load_transactions("nonexistent.xlsx")
        assert result.empty

    @patch("pandas.read_excel")
    def test_load_transactions_missing_columns(self, mock_read_excel):
        """Тест загрузки файла с отсутствующими колонками"""
        mock_read_excel.return_value = pd.DataFrame({"Wrong Column": [1, 2, 3]})

        result = load_transactions("dummy_path.xlsx")
        assert result.empty
