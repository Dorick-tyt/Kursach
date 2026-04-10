import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

"""
Вспомогательные функции для страницы «Главная».
Содержит функции для работы с транзакциями, API и форматированием данных.
"""


# Настройка логирования
def setup_logger() -> logging.Logger:
    """Настройка логгера для модуля utils"""
    log_file = "logs/utils.log"
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    utils_logger = logging.getLogger("utils")
    utils_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    if utils_logger.hasHandlers():
        utils_logger.handlers.clear()

    utils_logger.addHandler(file_handler)
    return utils_logger


logger = setup_logger()


def get_greeting(current_time: Optional[datetime] = None) -> str:
    """
    Возвращает приветствие в зависимости от времени суток.

    Args:
        current_time: Текущее время (если не указано, используется текущее)

    Returns:
        Приветствие: "Доброе утро" / "Добрый день" / "Добрый вечер" / "Доброй ночи"
    """
    if current_time is None:
        current_time = datetime.now()

    hour = current_time.hour
    logger.debug(f"Определение приветствия для часа: {hour}")

    if 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"


def load_transactions(file_path: str = "data/operations.xlsx") -> pd.DataFrame:
    """
    Загружает транзакции из Excel файла.

    Args:
        file_path: Путь к Excel файлу

    Returns:
        DataFrame с транзакциями
    """
    try:
        logger.info(f"Загрузка транзакций из файла: {file_path}")
        df_raw = pd.read_excel(file_path)
        logger.info(f"Загружено {len(df_raw)} строк из {file_path}")

        result_df = pd.DataFrame()

        # Определяем колонку с датой
        date_column = None
        for col in df_raw.columns:
            if col in ["Дата операции", "Дата платежа", "Date", "date"]:
                date_column = col
                break

        if date_column:
            result_df["date"] = pd.to_datetime(
                df_raw[date_column], format="%d.%m.%Y %H:%M:%S", errors="coerce"
            )
            logger.debug(f"Колонка с датой: '{date_column}'")
        else:
            logger.error("Не найдена колонка с датой")
            return pd.DataFrame()

        # Определяем колонку с суммой
        amount_column = None
        for col in df_raw.columns:
            if col in ["Сумма операции", "Сумма платежа", "Amount", "amount"]:
                amount_column = col
                break

        if amount_column:
            result_df["amount"] = pd.to_numeric(df_raw[amount_column], errors="coerce")
            logger.debug(f"Колонка с суммой: '{amount_column}'")
        else:
            logger.error("Не найдена колонка с суммой")
            return pd.DataFrame()

        # Определяем колонку с категорией
        category_column = None
        for col in df_raw.columns:
            if col in ["Категория", "Category", "category"]:
                category_column = col
                break

        if category_column:
            result_df["category"] = df_raw[category_column].fillna("").astype(str)
            logger.debug(f"Колонка с категорией: '{category_column}'")

        # Определяем колонку с описанием
        description_column = None
        for col in df_raw.columns:
            if col in ["Описание", "Description", "description"]:
                description_column = col
                break

        if description_column:
            result_df["description"] = df_raw[description_column].fillna("").astype(str)
            logger.debug(f"Колонка с описанием: '{description_column}'")

        # Определяем колонку с номером карты
        card_column = None
        for col in df_raw.columns:
            if col in ["Номер карты", "Card", "card"]:
                card_column = col
                break

        if card_column:
            result_df["card_number"] = df_raw[card_column].fillna("").astype(str)
            logger.debug(f"Колонка с номером карты: '{card_column}'")

        # Удаляем строки с пустыми датами или суммами
        before_count = len(result_df)
        result_df = result_df.dropna(subset=["date", "amount"])
        after_count = len(result_df)

        logger.info(f"Удалено строк с пустыми значениями: {before_count - after_count}")
        logger.info(f"После обработки осталось {len(result_df)} транзакций")

        return result_df

    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {file_path} - {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        return pd.DataFrame()


def get_card_info(transactions_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Получает информацию по каждой карте:
    - последние 4 цифры
    - общая сумма расходов
    - кешбэк (1 рубль на каждые 100 рублей)

    Args:
        transactions_df: DataFrame с транзакциями

    Returns:
        Список словарей с информацией по картам
    """
    logger.info("Получение информации по картам")

    if transactions_df.empty or "card_number" not in transactions_df.columns:
        logger.warning("Нет данных для получения информации по картам")
        return []

    cards_info = []

    # Группируем по номеру карты
    for card_number, group in transactions_df.groupby("card_number"):
        if not card_number or card_number == "" or pd.isna(card_number):
            continue

        # Берём только расходы (отрицательные суммы)
        expenses = group[group["amount"] < 0]["amount"].sum()
        total_spent = abs(expenses)

        # Кешбэк: 1 рубль на каждые 100 рублей
        cashback = round(total_spent / 100, 2)

        # Последние 4 цифры карты
        card_str = str(card_number)
        last_digits = card_str[-4:] if len(card_str) >= 4 else card_str

        cards_info.append(
            {
                "last_digits": last_digits,
                "total_spent": round(total_spent, 2),
                "cashback": cashback,
            }
        )

    logger.info(f"Получена информация по {len(cards_info)} картам")
    return cards_info


def get_top_transactions(
    transactions_df: pd.DataFrame, top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    Получает топ-N транзакций по сумме платежа.

    Args:
        transactions_df: DataFrame с транзакциями
        top_n: Количество транзакций (по умолчанию 5)

    Returns:
        Список топ транзакций
    """
    logger.info(f"Получение топ-{top_n} транзакций")

    if transactions_df.empty:
        logger.warning("Нет данных для получения топ транзакций")
        return []

    # Берём расходы (отрицательные суммы) и сортируем по убыванию
    expenses = transactions_df[transactions_df["amount"] < 0].copy()
    expenses["amount_abs"] = expenses["amount"].abs()
    top_expenses = expenses.nlargest(top_n, "amount_abs")

    result = []
    for _, row in top_expenses.iterrows():
        result.append(
            {
                "date": (
                    row["date"].strftime("%d.%m.%Y") if pd.notna(row["date"]) else ""
                ),
                "amount": round(abs(row["amount"]), 2),
                "category": row.get("category", ""),
                "description": row.get("description", ""),
            }
        )

    logger.info(f"Получено {len(result)} топ транзакций")
    return result


def get_currency_rates(currencies: List[str] = None) -> List[Dict[str, Any]]:
    """
    Получает курсы валют с API.

    Args:
        currencies: Список кодов валют (по умолчанию ['USD', 'EUR'])

    Returns:
        Список словарей с курсами валют
    """
    if currencies is None:
        currencies = ["USD", "EUR"]

    logger.info(f"Запрос курсов валют для: {currencies}")
    rates = []

    try:
        # Используем API exchangerate.host
        url = "https://api.exchangerate.host/latest"
        params = {"base": "RUB", "symbols": ",".join(currencies)}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        rates_data = data.get("rates", {})

        for currency in currencies:
            rate = rates_data.get(currency)
            if rate:
                rates.append({"currency": currency, "rate": round(rate, 2)})

        logger.info(f"Получены курсы валют: {rates}")

    except requests.RequestException as e:
        logger.error(f"Ошибка получения курсов валют: {e}")
        # Возвращаем заглушки при ошибке
        for currency in currencies:
            rates.append({"currency": currency, "rate": 0.0})

    return rates


def get_stock_prices(stocks: List[str] = None) -> List[Dict[str, Any]]:
    """
    Получает стоимости акций из S&P500.

    Args:
        stocks: Список тикеров акций (по умолчанию топ-5 S&P500)

    Returns:
        Список словарей с ценами акций
    """
    if stocks is None:
        stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    logger.info(f"Запрос цен акций для: {stocks}")
    prices = []

    try:
        # Для реального API нужен API ключ
        # Используем тестовые данные для демонстрации
        test_prices = {
            "AAPL": 175.50,
            "MSFT": 330.20,
            "GOOGL": 138.75,
            "AMZN": 145.80,
            "TSLA": 248.50,
        }

        for stock in stocks:
            price = test_prices.get(stock, 0.0)
            prices.append({"stock": stock, "price": round(price, 2)})

        logger.info(f"Получены цены акций: {prices}")

    except Exception as e:
        logger.error(f"Ошибка получения цен акций: {e}")
        for stock in stocks:
            prices.append({"stock": stock, "price": 0.0})

    return prices


def save_to_json_file(data: Dict[str, Any], filename: str) -> None:
    """
    Сохраняет данные в JSON файл.

    Args:
        data: Данные для сохранения
        filename: Имя файла
    """
    try:
        output_path = Path("reports") / filename
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Данные сохранены в файл: {output_path}")

    except Exception as e:
        logger.error(f"Ошибка сохранения файла {filename}: {e}")
