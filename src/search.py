import json
import logging
from typing import List, Dict, Any
from pathlib import Path
import os
import pandas as pd

"""
Модуль для сервисов поиска транзакций.
Содержит функцию простого поиска по описанию или категории.
"""
# Настройка логирования
def setup_logger() -> logging.Logger:
    """Настройка логгера для модуля services"""
    log_file = "logs/services.log"
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    services_logger = logging.getLogger("services")
    services_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    if services_logger.hasHandlers():
        services_logger.handlers.clear()

    services_logger.addHandler(file_handler)
    return services_logger


logger = setup_logger()


def load_transactions_from_excel(excel_file_path: str = "data/operations.xlsx") -> List[Dict[str, Any]]:
    """
    Загружает транзакции из Excel файла и возвращает в виде списка словарей.

    Args:
        excel_file_path: Путь к Excel файлу

    Returns:
        Список словарей с транзакциями
    """
    try:
        logger.info(f"Загрузка транзакций из файла: {excel_file_path}")
        df_raw = pd.read_excel(excel_file_path)
        logger.info(f"Загружено {len(df_raw)} строк из {excel_file_path}")

        transactions = []

        # Определяем колонки
        date_column = None
        for col in df_raw.columns:
            if col in ['Дата операции', 'Дата платежа', 'Date', 'date']:
                date_column = col
                break

        amount_column = None
        for col in df_raw.columns:
            if col in ['Сумма операции', 'Сумма платежа', 'Amount', 'amount']:
                amount_column = col
                break

        category_column = None
        for col in df_raw.columns:
            if col in ['Категория', 'Category', 'category']:
                category_column = col
                break

        description_column = None
        for col in df_raw.columns:
            if col in ['Описание', 'Description', 'description']:
                description_column = col
                break

        card_column = None
        for col in df_raw.columns:
            if col in ['Номер карты', 'Card', 'card']:
                card_column = col
                break

        # Преобразуем каждую строку в словарь
        for _, row in df_raw.iterrows():
            transaction = {}

            # Дата
            if date_column and pd.notna(row[date_column]):
                try:
                    date_val = pd.to_datetime(row[date_column], format='%d.%m.%Y %H:%M:%S', errors='coerce')
                    transaction['date'] = date_val.strftime('%d.%m.%Y') if pd.notna(date_val) else ""
                except (ValueError, TypeError):
                    transaction['date'] = ""
            else:
                transaction['date'] = ""

            # Сумма
            if amount_column and pd.notna(row[amount_column]):
                try:
                    transaction['amount'] = float(row[amount_column])
                except (ValueError, TypeError):
                    transaction['amount'] = 0.0
            else:
                transaction['amount'] = 0.0

            # Категория
            if category_column and pd.notna(row[category_column]):
                transaction['category'] = str(row[category_column])
            else:
                transaction['category'] = ""

            # Описание
            if description_column and pd.notna(row[description_column]):
                transaction['description'] = str(row[description_column])
            else:
                transaction['description'] = ""

            # Номер карты (последние 4 цифры)
            if card_column and pd.notna(row[card_column]):
                card_str = str(row[card_column])
                if len(card_str) >= 4:
                    transaction['card_last_digits'] = card_str[-4:]
                else:
                    transaction['card_last_digits'] = card_str

            # Тип операции (расход/доход)
            transaction['amount_type'] = "expense" if transaction['amount'] < 0 else "income"
            transaction['amount_abs'] = abs(transaction['amount'])

            transactions.append(transaction)

        logger.info(f"Загружено и преобразовано {len(transactions)} транзакций")
        return transactions

    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {excel_file_path} - {e}")
        return []
    except pd.errors.EmptyDataError as e:
        logger.error(f"Файл пуст: {excel_file_path} - {e}")
        return []
    except PermissionError as e:
        logger.error(f"Нет доступа к файлу: {excel_file_path} - {e}")
        return []
    except ValueError as e:
        logger.error(f"Ошибка значения при чтении файла: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка загрузки файла {excel_file_path}: {type(e).__name__}: {e}")
        return []


def simple_search(
    transactions: List[Dict[str, Any]], 
    search_query: str
) -> List[Dict[str, Any]]:
    """
    Простой поиск транзакций по запросу в описании или категории.

    Args:
        transactions: Список словарей с транзакциями
        search_query: Строка для поиска

    Returns:
        Список транзакций, соответствующих запросу
    """
    logger.info(f"Поиск транзакций по запросу: '{search_query}'")

    if not transactions:
        logger.warning("Список транзакций пуст")
        return []

    if not search_query or not search_query.strip():
        logger.warning("Пустой поисковый запрос")
        return []

    search_lower = search_query.lower().strip()
    results = []

    for transaction in transactions:
        # Поиск в категории
        category_match = search_lower in transaction.get('category', '').lower()
        # Поиск в описании
        description_match = search_lower in transaction.get('description', '').lower()

        if category_match or description_match:
            # Возвращаем копию транзакции без поля amount_abs (оно служебное)
            result_item = {
                "date": transaction.get('date', ''),
                "amount": transaction.get('amount_abs', 0),
                "amount_type": transaction.get('amount_type', ''),
                "category": transaction.get('category', ''),
                "description": transaction.get('description', '')
            }
            if 'card_last_digits' in transaction:
                result_item['card_last_digits'] = transaction['card_last_digits']

            results.append(result_item)

    logger.info(f"Найдено {len(results)} транзакций по запросу '{search_query}'")
    return results


def simple_search_json(
    transactions: List[Dict[str, Any]], 
    search_query: str,
    save_to_file: bool = True
) -> str:
    """
    Поиск транзакций и возврат JSON-ответа.

    Args:
        transactions: Список словарей с транзакциями
        search_query: Строка для поиска
        save_to_file: Сохранять ли результат в файл

    Returns:
        JSON-строка с результатами поиска
    """
    logger.info(f"=== ЗАПРОС ПРОСТОГО ПОИСКА ===")
    logger.info(f"Поисковый запрос: '{search_query}'")

    try:
        results = simple_search(transactions, search_query)

        response = {
            "query": search_query,
            "count": len(results),
            "transactions": results
        }

        # Сохраняем результат в JSON файл
        if save_to_file:
            from datetime import datetime
            output_path = Path("reports") / f"search_{search_query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path.parent.mkdir(exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"Результаты поиска сохранены в файл: {output_path}")

        logger.info(f"Найдено {len(results)} транзакций")
        return json.dumps(response, ensure_ascii=False, indent=2)

    except (TypeError, ValueError) as e:
        logger.error(f"Ошибка при обработке данных: {e}")
        error_response = {
            "query": search_query,
            "error": str(e),
            "count": 0,
            "transactions": []
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"Ошибка ввода-вывода: {e}")
        error_response = {
            "query": search_query,
            "error": str(e),
            "count": 0,
            "transactions": []
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


if __name__ == "__main__":

    # Переходим в корень проекта
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Пример использования
    print("=== ПРИМЕР ПРОСТОГО ПОИСКА ===")

    # Загружаем транзакции из Excel
    excel_path = "data/operations.xlsx"
    transactions_data = load_transactions_from_excel(excel_path)

    if not transactions_data:
        print("Не удалось загрузить данные. Создаём тестовые данные...")
        # Тестовые данные для демонстрации
        transactions_data = [
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

    # Пример 1: Поиск по категории
    print("\n1. Поиск по категории 'Супермаркеты':")
    result1 = simple_search_json(transactions_data, "Супермаркеты", save_to_file=False)
    print(result1)

    # Пример 2: Поиск по описанию
    print("\n2. Поиск по описанию 'Магнит':")
    result2 = simple_search_json(transactions_data, "Магнит", save_to_file=False)
    print(result2)

    # Пример 3: Поиск без результатов
    print("\n3. Поиск по 'Несуществующая категория':")
    result3 = simple_search_json(transactions_data, "Несуществующая категория", save_to_file=False)
    print(result3)

    # Пример 4: Пустой запрос
    print("\n4. Пустой запрос:")
    result4 = simple_search_json(transactions_data, "", save_to_file=False)
    print(result4)