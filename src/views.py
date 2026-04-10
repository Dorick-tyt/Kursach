import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.utils import (
    get_card_info,
    get_currency_rates,
    get_greeting,
    get_stock_prices,
    get_top_transactions,
    load_transactions,
    save_to_json_file,
)

"""
Модуль для страницы «Главная».
Содержит основную функцию, формирующую JSON-ответ для главной страницы.
"""


# Настройка логирования
def setup_logger() -> logging.Logger:
    """Настройка логгера для модуля views"""
    log_file = "logs/views.log"
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    views_logger = logging.getLogger("views")
    views_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    if views_logger.hasHandlers():
        views_logger.handlers.clear()

    views_logger.addHandler(file_handler)
    return views_logger


logger = setup_logger()


def main_page(date_time_str: Optional[str] = None) -> str:
    """
    Главная функция, генерирующая JSON-ответ для главной страницы.

    Args:
        date_time_str: Строка с датой и временем в формате YYYY-MM-DD HH:MM:SS
                       Если не указана, используется текущее время.

    Returns:
        JSON-строка с данными для главной страницы
    """
    logger.info(f"=== ЗАПРОС ГЛАВНОЙ СТРАНИЦЫ ===")
    logger.info(f"Входной параметр: {date_time_str}")

    try:
        # Парсим дату и время
        if date_time_str:
            try:
                current_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
                logger.info(f"Используем переданное время: {current_time}")
            except ValueError as e:
                logger.error(f"Неверный формат даты: {date_time_str} - {e}")
                current_time = datetime.now()
                logger.info(f"Используем текущее время: {current_time}")
        else:
            current_time = datetime.now()
            logger.info(f"Используем текущее время: {current_time}")

        # Загружаем транзакции
        logger.info("Загрузка транзакций...")
        transactions_df = load_transactions("data/operations.xlsx")

        if transactions_df.empty:
            logger.warning("Транзакции не загружены или файл пуст")

        # Формируем ответ
        logger.info("Формирование JSON-ответа...")
        response: Dict[str, Any] = {
            "greeting": get_greeting(current_time),
            "cards": get_card_info(transactions_df),
            "top_transactions": get_top_transactions(transactions_df, 5),
            "currency_rates": get_currency_rates(["USD", "EUR"]),
            "stock_prices": get_stock_prices(["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
        }

        # Сохраняем результат в JSON файл
        filename = f"main_page_{current_time.strftime('%Y%m%d_%H%M%S')}.json"
        save_to_json_file(response, filename)

        json_response = json.dumps(response, ensure_ascii=False, indent=2)
        logger.info("JSON-ответ успешно сформирован")
        logger.info(f"Размер ответа: {len(json_response)} символов")

        return json_response

    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}", exc_info=True)
        error_response = {
            "error": str(e),
            "greeting": get_greeting(),
            "cards": [],
            "top_transactions": [],
            "currency_rates": [],
            "stock_prices": [],
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Примеры использования
    print("=== ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ===")

    print("\n1. Текущее время:")
    response1 = main_page()
    print(response1)

    print("\n2. Утро (08:00:00):")
    response2 = main_page("2024-01-15 08:00:00")
    print(response2)

    print("\n3. День (14:30:00):")
    response3 = main_page("2024-01-15 14:30:00")
    print(response3)

    print("\n4. Вечер (20:00:00):")
    response4 = main_page("2024-01-15 20:00:00")
    print(response4)

    print("\n5. Ночь (01:00:00):")
    response5 = main_page("2024-01-15 01:00:00")
    print(response5)

    print("\n6. Неверный формат даты:")
    response6 = main_page("invalid-date")
    print(response6)
