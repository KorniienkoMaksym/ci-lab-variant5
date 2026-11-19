"""Базова версія: працює правильно, але неефективно.

Так часто пишуть код, коли думають лише про результат.
Позначки «НЕЕФЕКТИВНО n» — місця, виправлені
в optimized.py.
"""
from datetime import datetime

import pandas as pd

from bench.common import (CITY_IDS, COLUMNS, EU_DAILY_2030,
                          MIN_HOURS, WHO_DAILY, YEARS,
                          raw_file, who_level)

FMT = "%Y-%m-%d %H:%M:%S"


def compute_indicators() -> pd.DataFrame:
    rows = []
    for city_id in CITY_IDS:
        for year in YEARS:
            # НЕЕФЕКТИВНО 1: файл читається заново для
            # кожного міста, усі стовпці, типи «вгадуються»
            df = pd.read_csv(raw_file(year))
            df = df[df["city_id"] == city_id].copy()

            # НЕЕФЕКТИВНО 2: розбір дати рядок за рядком
            df["logged_at"] = df["logged_at"].apply(
                lambda s: datetime.strptime(s, FMT))
            df = df.drop_duplicates(subset=["logged_at"])

            # НЕЕФЕКТИВНО 3: перевірка рядок за рядком
            ok = df.apply(lambda r: 0 <= r["pm25"] <= 1000,
                          axis=1)
            df = df[ok]
            df["date"] = df["logged_at"].apply(
                lambda t: t.date())

            # НЕЕФЕКТИВНО 4: цикл по днях — для кожного дня
            # переглядається вся таблиця міста за рік
            days = pd.date_range(f"{year}-01-01",
                                 f"{year}-12-31")
            daily = []
            for day in days:
                values = df[df["date"] == day.date()]["pm25"]
                if len(values) >= MIN_HOURS:
                    daily.append(values.mean())

            # НЕЕФЕКТИВНО 5: підрахунки списками Python
            annual = sum(daily) / len(daily)
            rows.append({
                "city_id": city_id, "year": year,
                "annual_mean": annual,
                "valid_days": len(daily),
                "days_in_year": len(days),
                "days_over_15":
                    len([v for v in daily if v > WHO_DAILY]),
                "days_over_25":
                    len([v for v in daily
                         if v > EU_DAILY_2030]),
                "completeness_pct":
                    len(daily) / len(days) * 100,
                "who_level": who_level(annual),
            })
    result = pd.DataFrame(rows).set_index(["city_id", "year"])
    return result[COLUMNS]
