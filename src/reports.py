import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, Union

import pandas as pd
from pandas import DataFrame


# Настройка логирования
def setup_logger() -> logging.Logger:
    """Настройка логгера для модуля reports"""
    log_file = "logs/reports.log"
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    reports_logger = logging.getLogger("reports")
    reports_logger.setLevel(logging.DEBUG)

    # Файловый обработчик
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Удаляем старые обработчики, чтобы не дублировать
    if reports_logger.hasHandlers():
        reports_logger.handlers.clear()

    reports_logger.addHandler(file_handler)
    return reports_logger


# Логгер для модуля
report_logger: logging.Logger = setup_logger()


# Декоратор для сохранения отчётов
def report_decorator(filename: Optional[str] = None) -> Callable:
    """
    Декоратор для сохранения результата функции отчёта в файл.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Выполняем функцию
            result: Union[DataFrame, Any] = func(*args, **kwargs)

            # Определяем имя файла
            if filename is None:
                default_name: str = (
                    f"report_{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                output_filename: str = default_name
            else:
                output_filename = filename

            # Сохраняем результат в JSON файл
            output_path: Path = Path("reports") / output_filename
            output_path.parent.mkdir(exist_ok=True)

            # Преобразуем DataFrame в словарь, если нужно
            if isinstance(result, DataFrame):
                result_dict: Any = result.to_dict(orient="records")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
                report_logger.info(f"Отчёт сохранён в файл: {output_path}")
            elif result is not None:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                report_logger.info(f"Отчёт сохранён в файл: {output_path}")

            return result

        return wrapper

    return decorator


def load_transactions(file_path: str = "data/operations.xlsx") -> DataFrame:
    """Загружает транзакции из Excel файла."""
    try:
        print(f"Попытка загрузить файл: {file_path}")

        df_raw: DataFrame = pd.read_excel(file_path)
        print(f"Файл прочитан. Строк: {len(df_raw)}, Колонок: {len(df_raw.columns)}")

        result_df: DataFrame = pd.DataFrame()

        # Определяем колонку с датой
        date_column: Optional[str] = None
        for col in df_raw.columns:
            if col in ["Дата операции", "Дата платежа", "Date", "date"]:
                date_column = col
                break

        if date_column:
            print(f"Найдена колонка с датой: '{date_column}'")
            result_df["date"] = pd.to_datetime(
                df_raw[date_column], format="%d.%m.%Y %H:%M:%S", errors="coerce"
            )
            print(
                f"Преобразовано дат: {result_df['date'].notna().sum()} из {len(df_raw)}"
            )
        else:
            print(f"Не найдена колонка с датой")
            return pd.DataFrame()

        # Определяем колонку с суммой
        amount_column: Optional[str] = None
        for col in df_raw.columns:
            if col in ["Сумма операции", "Сумма платежа", "Amount", "amount"]:
                amount_column = col
                break

        if amount_column:
            print(f"Найдена колонка с суммой: '{amount_column}'")
            result_df["amount"] = pd.to_numeric(df_raw[amount_column], errors="coerce")
            print(
                f"Преобразовано сумм: {result_df['amount'].notna().sum()} из {len(df_raw)}"
            )
        else:
            print(f"Не найдена колонка с суммой")
            return pd.DataFrame()

        # Определяем колонку с категорией
        category_column: Optional[str] = None
        for col in df_raw.columns:
            if col in ["Категория", "Category", "category"]:
                category_column = col
                break

        if category_column:
            print(f"Найдена колонка с категорией: '{category_column}'")
            result_df["category"] = df_raw[category_column].fillna("").astype(str)
        else:
            print(f"Не найдена колонка с категорией")
            result_df["category"] = ""

        # Определяем колонку с описанием
        description_column: Optional[str] = None
        for col in df_raw.columns:
            if col in ["Описание", "Description", "description"]:
                description_column = col
                break

        if description_column:
            print(f"Найдена колонка с описанием: '{description_column}'")
            result_df["description"] = df_raw[description_column].fillna("").astype(str)
        else:
            print(f"Не найдена колонка с описанием")
            result_df["description"] = ""

        # Добавляем дополнительные колонки
        if "Валюта операции" in df_raw.columns:
            result_df["currency"] = df_raw["Валюта операции"].fillna("").astype(str)

        if "Статус" in df_raw.columns:
            result_df["status"] = df_raw["Статус"].fillna("").astype(str)

        # Удаляем строки с пустыми значениями
        before_count: int = len(result_df)
        result_df = result_df.dropna(subset=["date", "amount"])
        after_count: int = len(result_df)

        print(f"Удалено строк с пустыми значениями: {before_count - after_count}")

        if result_df.empty:
            print("После очистки не осталось данных")
            return pd.DataFrame()

        print(
            f"Диапазон сумм: от {result_df['amount'].min()} до {result_df['amount'].max()}"
        )
        report_logger.info(f"Загружено {len(result_df)} транзакций из {file_path}")
        print(f"Загрузка успешна! Обработано {len(result_df)} транзакций")

        return result_df

    except Exception as e:
        print(f"Ошибка загрузки файла {file_path}: {type(e).__name__}: {e}")
        report_logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        return pd.DataFrame()


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Преобразует строку с датой в объект datetime."""
    if date_str is None:
        return None

    try:
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Неверный формат даты: {date_str}")
    except ValueError as e:
        report_logger.error(f"Ошибка парсинга даты: {e}")
        return None


def filter_by_last_three_months(
    data_df: DataFrame, date: Optional[str] = None
) -> DataFrame:
    """Фильтрует транзакции за последние 3 месяца от указанной даты."""
    if data_df.empty:
        report_logger.warning("Получен пустой DataFrame")
        return data_df

    if date is None:
        current_date: datetime = data_df["date"].max()
        report_logger.info(f"Дата не указана, используем максимальную: {current_date}")
    else:
        current_date_parsed: Optional[datetime] = parse_date(date)
        if current_date_parsed is None:
            current_date = data_df["date"].max()
            report_logger.warning(
                f"Не удалось распарсить дату, используем максимальную: {current_date}"
            )
        else:
            current_date = current_date_parsed

    three_months_ago: datetime = current_date - timedelta(days=90)
    print(
        f"Фильтрация с {three_months_ago.strftime('%Y-%m-%d')} по {current_date.strftime('%Y-%m-%d')}"
    )

    filtered_df: DataFrame = data_df[
        (data_df["date"] >= three_months_ago) & (data_df["date"] <= current_date)
    ].copy()

    report_logger.debug(
        f"Отфильтровано {len(filtered_df)} транзакций за последние 3 месяца"
    )
    print(f"Найдено транзакций: {len(filtered_df)}")

    return filtered_df


@report_decorator()
def spending_by_category(
    transactions_df: DataFrame, category: str, date: Optional[str] = None
) -> DataFrame:
    """Отчёт о тратах по заданной категории за последние 3 месяца."""
    report_logger.info(f"Формирование отчёта по категории '{category}'")

    if transactions_df.empty:
        report_logger.warning("DataFrame с транзакциями пуст")
        return pd.DataFrame()

    filtered_df: DataFrame = filter_by_last_three_months(transactions_df, date)

    if filtered_df.empty:
        report_logger.warning("Нет транзакций за последние 3 месяца")
        return pd.DataFrame()

    if "category" in filtered_df.columns:
        category_df: DataFrame = filtered_df[
            filtered_df["category"]
            .astype(str)
            .str.contains(category, case=False, na=False)
        ].copy()
        print(f"Найдено транзакций по категории '{category}': {len(category_df)}")
    else:
        report_logger.error("В данных нет колонки 'category'")
        return pd.DataFrame()

    if category_df.empty:
        print(f"Категория '{category}' не найдена.")
        if "category" in filtered_df.columns:
            print("Доступные категории:")
            for cat_name in filtered_df["category"].value_counts().head(10).index:
                print(f"  - {cat_name}")
        return pd.DataFrame()

    result_columns = ["date", "amount", "category"]
    if "description" in category_df.columns:
        result_columns.append("description")

    result_df: DataFrame = category_df[result_columns].copy()
    result_df = result_df.sort_values("date", ascending=False)

    report_logger.info(f"Найдено {len(result_df)} транзакций по категории '{category}'")
    return result_df


@report_decorator()
def spending_by_weekday(
    transactions_df: DataFrame, date: Optional[str] = None
) -> DataFrame:
    """Отчёт о средних тратах по дням недели за последние 3 месяца."""
    report_logger.info("Формирование отчёта о тратах по дням недели")

    if transactions_df.empty:
        report_logger.warning("DataFrame с транзакциями пуст")
        return pd.DataFrame()

    filtered_df: DataFrame = filter_by_last_three_months(transactions_df, date)

    if filtered_df.empty:
        report_logger.warning("Нет транзакций за последние 3 месяца")
        return pd.DataFrame()

    filtered_df["weekday"] = filtered_df["date"].dt.day_name()
    filtered_df["weekday_num"] = filtered_df["date"].dt.weekday

    weekday_spending: DataFrame = (
        filtered_df.groupby(["weekday_num", "weekday"])["amount"]
        .agg(["mean", "count", "sum"])
        .reset_index()
    )
    weekday_spending.columns = [
        "weekday_num",
        "day_of_week",
        "average_spending",
        "transaction_count",
        "total_spending",
    ]
    weekday_spending = weekday_spending.sort_values("weekday_num").drop(
        "weekday_num", axis=1
    )

    report_logger.info(f"Сформирован отчёт по {len(weekday_spending)} дням недели")
    return weekday_spending


@report_decorator()
def spending_by_workday(
    transactions_df: DataFrame, date: Optional[str] = None
) -> DataFrame:
    """Отчёт о средних тратах в рабочие и выходные дни за последние 3 месяца."""
    report_logger.info("Формирование отчёта о тратах в рабочие и выходные дни")

    if transactions_df.empty:
        report_logger.warning("DataFrame с транзакциями пуст")
        return pd.DataFrame()

    filtered_df: DataFrame = filter_by_last_three_months(transactions_df, date)

    if filtered_df.empty:
        report_logger.warning("Нет транзакций за последние 3 месяца")
        return pd.DataFrame()

    filtered_df["weekday"] = filtered_df["date"].dt.day_name()
    filtered_df["weekday_num"] = filtered_df["date"].dt.weekday
    filtered_df["day_type"] = filtered_df["weekday_num"].apply(
        lambda x: "working" if x < 5 else "weekend"
    )

    workday_spending: DataFrame = (
        filtered_df.groupby("day_type")["amount"]
        .agg(["mean", "count", "sum"])
        .reset_index()
    )
    workday_spending.columns = [
        "day_type",
        "average_spending",
        "transaction_count",
        "total_spending",
    ]
    workday_spending["day_type"] = workday_spending["day_type"].map(
        {"working": "Рабочий день", "weekend": "Выходной день"}
    )

    report_logger.info(f"Сформирован отчёт")
    return workday_spending


if __name__ == "__main__":
    import os

    project_root: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("Текущая рабочая директория:", os.getcwd())

    excel_file_path: str = "data/operations.xlsx"

    if os.path.exists(excel_file_path):
        print(f"Файл найден: {excel_file_path}")
    else:
        print(f"Файл не найден: {excel_file_path}")
        exit()

    print("\nЗагрузка транзакций из Excel...")
    transactions_data: DataFrame = load_transactions(excel_file_path)

    if transactions_data.empty:
        print("Не удалось загрузить данные.")
    else:
        print(f"Загружено {len(transactions_data)} транзакций")
        print(f"Колонки: {list(transactions_data.columns)}")
        print(
            f"Диапазон дат: {transactions_data['date'].min()} - {transactions_data['date'].max()}"
        )

        print("\n" + "=" * 50)
        print("Отчёт по дням недели")
        print("=" * 50)
        result2 = spending_by_weekday(transactions_data)
        print(result2)

        print("\n" + "=" * 50)
        print("Отчёт по рабочим/выходным дням")
        print("=" * 50)
        result3 = spending_by_workday(transactions_data)
        print(result3)
