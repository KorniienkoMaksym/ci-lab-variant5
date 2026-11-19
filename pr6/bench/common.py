"""Спільні налаштування навантаження ПР6.

Навантаження — розрахунок індикаторів якості повітря
з ПР4 (ISO 37120, ЦСР 11.6.2) для двох міст за три роки.
Функціональна одиниця R — один повний розрахунок
таблиці індикаторів (2 міста × 3 роки).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # папка pr6
RAW = ROOT / "data" / "raw"

YEARS = [2021, 2022, 2023]
CITY_IDS = {2: "Київ", 219: "Харків"}       # id з файлу міст

MIN_HOURS = 18       # доба дійсна, якщо є ≥ 18 вимірів
WHO_DAILY = 15       # ВООЗ 2021, середньодобова, мкг/м³
EU_DAILY_2030 = 25   # ЄС з 2030 р., середньодобова

COLUMNS = ["annual_mean", "valid_days", "days_in_year",
           "days_over_15", "days_over_25",
           "completeness_pct", "who_level"]


def raw_file(year: int) -> Path:
    name = f"saveecobot_cities_pm25_and_aqi_pm25_{year}.csv"
    return RAW / name


def who_level(x: float) -> str:
    """Рівень за проміжними цілями ВООЗ (як у ПР4)."""
    levels = [(5, "настанова ВООЗ"), (10, "IT-4"),
              (15, "IT-3"), (25, "IT-2"), (35, "IT-1")]
    for limit, name in levels:
        if x <= limit:
            return name
    return "гірше IT-1"


def normalize(ind):
    """Таблиця в єдиному вигляді для порівняння версій:
    стовпці замість індексу, цілі типи, округлення."""
    t = ind.reset_index().sort_values(["city_id", "year"])
    ints = ["city_id", "year", "valid_days", "days_in_year",
            "days_over_15", "days_over_25"]
    t = t.astype({c: "int64" for c in ints})
    t = t.round({"annual_mean": 6, "completeness_pct": 6})
    return t.reset_index(drop=True)
