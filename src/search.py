import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

"""
Модуль для поиска транзакций по описанию или категории.
Возвращает JSON-ответ со всеми транзакциями, содержащими запрос.
"""


# Настройка логирования
def setup_logger() -> logging.Logger:
    """Настройка логгера для модуля search"""
    log_file = "logs/search.log"
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    search_logger = logging.getLogger("search")
    search_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    if search_logger.hasHandlers():
        search_logger.handlers.clear()

    search_logger.addHandler(file_handler)
    return search_logger


logger = setup_logger()


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

        # Определяем колонку с описанием
        description_column = None
        for col in df_raw.columns:
            if col in ["Описание", "Description", "description"]:
                description_column = col
                break

        if description_column:
            result_df["description"] = df_raw[description_column].fillna("").astype(str)

        # Определяем колонку с номером карты
        card_column = None
        for col in df_raw.columns:
            if col in ["Номер карты", "Card", "card"]:
                card_column = col
                break

        if card_column:
            result_df["card_number"] = df_raw[card_column].fillna("").astype(str)

        # Удаляем строки с пустыми датами или суммами
        result_df = result_df.dropna(subset=["date", "amount"])

        logger.info(f"После обработки осталось {len(result_df)} транзакций")
        return result_df

    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {file_path} - {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        return pd.DataFrame()


def search_transactions(
    search_query: str,
    transactions_df: Optional[pd.DataFrame] = None,
    file_path: str = "data/operations.xlsx",
) -> List[Dict[str, Any]]:
    """
    Поиск транзакций по запросу в описании или категории.

    Args:
        search_query: Строка для поиска
        transactions_df: DataFrame с транзакциями (если не передан, загружается из файла)
        file_path: Путь к Excel файлу

    Returns:
        Список транзакций, соответствующих запросу
    """
    logger.info(f"Поиск транзакций по запросу: '{search_query}'")

    if not search_query or not search_query.strip():
        logger.warning("Пустой поисковый запрос")
        return []

    # Загружаем данные, если не переданы
    if transactions_df is None:
        transactions_df = load_transactions(file_path)

    if transactions_df.empty:
        logger.warning("Нет данных для поиска")
        return []

    # Поиск в категории и описании (регистронезависимый)
    search_lower = search_query.lower().strip()

    mask = pd.Series([False] * len(transactions_df))

    if "category" in transactions_df.columns:
        mask = mask | transactions_df["category"].astype(str).str.lower().str.contains(
            search_lower, na=False
        )

    if "description" in transactions_df.columns:
        mask = mask | transactions_df["description"].astype(
            str
        ).str.lower().str.contains(search_lower, na=False)

    filtered_df = transactions_df[mask].copy()

    logger.info(f"Найдено {len(filtered_df)} транзакций по запросу '{search_query}'")

    # Формируем результат
    result = []
    for _, row in filtered_df.iterrows():
        transaction = {
            "date": row["date"].strftime("%d.%m.%Y") if pd.notna(row["date"]) else "",
            "amount": (
                round(abs(row["amount"]), 2)
                if row["amount"] < 0
                else round(row["amount"], 2)
            ),
            "amount_type": "expense" if row["amount"] < 0 else "income",
            "category": row.get("category", ""),
            "description": row.get("description", ""),
        }

        if "card_number" in row and row.get("card_number"):
            card_str = str(row["card_number"])
            transaction["card_last_digits"] = (
                card_str[-4:] if len(card_str) >= 4 else card_str
            )

        result.append(transaction)

    return result


def search_json(
    search_query: str,
    transactions_df: Optional[pd.DataFrame] = None,
    file_path: str = "data/operations.xlsx",
) -> str:
    """
    Поиск транзакций и возврат JSON-ответа.

    Args:
        search_query: Строка для поиска
        transactions_df: DataFrame с транзакциями (если не передан, загружается из файла)
        file_path: Путь к Excel файлу

    Returns:
        JSON-строка с результатами поиска
    """
    logger.info(f"=== ЗАПРОС ПОИСКА ===")
    logger.info(f"Поисковый запрос: '{search_query}'")

    try:
        results = search_transactions(search_query, transactions_df, file_path)

        response = {
            "query": search_query,
            "count": len(results),
            "transactions": results,
        }

        # Сохраняем результат в JSON файл
        output_path = (
            Path("reports")
            / f"search_{search_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(response, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Результаты поиска сохранены в файл: {output_path}")
        logger.info(f"Найдено {len(results)} транзакций")

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}", exc_info=True)
        error_response = {
            "query": search_query,
            "error": str(e),
            "count": 0,
            "transactions": [],
        }
        return json.dumps(error_response, ensure_ascii=False, indent=2)


if __name__ == "__main__":

    # Переходим в корень проекта
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("Текущая рабочая директория:", os.getcwd())
    print("=== ПРИМЕРЫ ПОИСКА ===")

    file_path = "data/operations.xlsx"

    # Загружаем транзакции один раз для всех примеров
    df = load_transactions("data/operations.xlsx")

    if not df.empty:
        # Пример 1: Поиск по категории
        print("\n1. Поиск по категории 'Супермаркеты':")
        result1 = search_json("Супермаркеты", df)
        data1 = json.loads(result1)
        print(f"Найдено: {data1['count']} транзакций")
        for t in data1["transactions"][:3]:
            print(f"  - {t['date']}: {t['description']} - {t['amount']} руб.")

        # Пример 2: Поиск по описанию
        print("\n2. Поиск по описанию 'Магнит':")
        result2 = search_json("Магнит", df)
        data2 = json.loads(result2)
        print(f"Найдено: {data2['count']} транзакций")
        for t in data2["transactions"][:3]:
            print(f"  - {t['date']}: {t['description']} - {t['amount']} руб.")

        # Пример 3: Поиск частичного совпадения
        print("\n3. Поиск по части 'Такси':")
        result3 = search_json("Такси", df)
        data3 = json.loads(result3)
        print(f"Найдено: {data3['count']} транзакций")
        for t in data3["transactions"][:3]:
            print(f"  - {t['date']}: {t['description']} - {t['amount']} руб.")

        # Пример 4: Поиск без результатов
        print("\n4. Поиск по 'Несуществующая категория':")
        result4 = search_json("Несуществующая категория", df)
        data4 = json.loads(result4)
        print(f"Найдено: {data4['count']} транзакций")

        # Пример 5: Пустой запрос
        print("\n5. Пустой запрос:")
        result5 = search_json("", df)
        data5 = json.loads(result5)
        print(f"Найдено: {data5['count']} транзакций")
    else:
        print("Не удалось загрузить данные для примеров")
