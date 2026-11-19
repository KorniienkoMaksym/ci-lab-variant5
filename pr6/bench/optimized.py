"""Оптимізована версія: той самий результат, менше роботи.

Позначки «ЗАМІСТЬ n» відповідають «НЕЕФЕКТИВНО n»
у baseline.py.
"""
import pandas as pd

from bench.common import (CITY_IDS, COLUMNS, EU_DAILY_2030,
                          MIN_HOURS, WHO_DAILY, YEARS,
                          raw_file, who_level)


def load() -> pd.DataFrame:
    # ЗАМІСТЬ 1: кожен файл читається один раз,
    # лише потрібні стовпці з явними типами
    frames = [pd.read_csv(raw_file(y),
                          usecols=["city_id", "pm25",
                                   "logged_at"],
                          dtype={"city_id": "int32",
                                 "pm25": "float64"})
              for y in YEARS]
    df = pd.concat(frames, ignore_index=True)
    df = df[df["city_id"].isin(list(CITY_IDS))]
    # ЗАМІСТЬ 2: векторний розбір дати з явним форматом
    df["logged_at"] = pd.to_datetime(
        df["logged_at"], format="%Y-%m-%d %H:%M:%S")
    df = df.drop_duplicates(subset=["city_id", "logged_at"])
    # ЗАМІСТЬ 3: векторна перевірка діапазону
    return df[df["pm25"].between(0, 1000)]


def compute_indicators() -> pd.DataFrame:
    df = load()
    # ЗАМІСТЬ 4: добові середні одним групуванням
    day = df["logged_at"].dt.floor("D")
    daily = (df.groupby(["city_id", day])["pm25"]
               .agg(["mean", "count"]))
    valid = daily.loc[daily["count"] >= MIN_HOURS, "mean"]
    city = valid.index.get_level_values("city_id")
    year = valid.index.get_level_values("logged_at").year

    # ЗАМІСТЬ 5: усі індикатори одним агрегуванням
    ind = valid.groupby([city, year]).agg(
        annual_mean="mean",
        valid_days="size",
        days_over_15=lambda s: int((s > WHO_DAILY).sum()),
        days_over_25=lambda s: int((s > EU_DAILY_2030).sum()),
    )
    ind.index.names = ["city_id", "year"]
    years = ind.index.get_level_values("year")
    ind["days_in_year"] = [366 if y % 4 == 0 else 365
                           for y in years]
    ind["completeness_pct"] = (ind["valid_days"]
                               / ind["days_in_year"] * 100)
    ind["who_level"] = ind["annual_mean"].map(who_level)
    return ind[COLUMNS]
