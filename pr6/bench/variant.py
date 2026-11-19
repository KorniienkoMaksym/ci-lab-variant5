from __future__ import annotations

import pandas as pd
import polars as pl

from bench.common import (
    CITY_IDS,
    COLUMNS,
    EU_DAILY_2030,
    MIN_HOURS,
    WHO_DAILY,
    YEARS,
    raw_file,
    who_level,
)


def compute_indicators() -> pd.DataFrame:
    lazy_frames = [
        pl.scan_csv(
            raw_file(y),
            null_values="NULL",
            schema_overrides={"city_id": pl.Int32, "pm25": pl.Float64, "logged_at": pl.String},
        ).select(["city_id", "pm25", "logged_at"])
        for y in YEARS
    ]

    lf = (
        pl.concat(lazy_frames)
        .filter(pl.col("city_id").is_in(list(CITY_IDS)))
        .with_columns(
            pl.col("logged_at").str.to_datetime(format="%Y-%m-%d %H:%M:%S")
        )
        .unique(subset=["city_id", "logged_at"])
        .filter(pl.col("pm25").is_between(0.0, 1000.0))
        .with_columns(
            pl.col("logged_at").dt.truncate("1d").alias("day")
        )
    )

    daily = (
        lf.group_by(["city_id", "day"])
        .agg(
            pl.col("pm25").mean().alias("daily_mean"),
            pl.col("pm25").count().alias("cnt"),
        )
        .filter(pl.col("cnt") >= MIN_HOURS)
        .with_columns(
            pl.col("day").dt.year().alias("year")
        )
    )

    annual_pl = (
        daily.group_by(["city_id", "year"])
        .agg(
            pl.col("daily_mean").mean().alias("annual_mean"),
            pl.col("daily_mean").count().alias("valid_days"),
            (pl.col("daily_mean") > WHO_DAILY).sum().alias("days_over_15"),
            (pl.col("daily_mean") > EU_DAILY_2030).sum().alias("days_over_25"),
        )
        .sort(["city_id", "year"])
        .collect()
    )

    df = annual_pl.to_pandas()
    df["days_in_year"] = [366 if y % 4 == 0 else 365 for y in df["year"]]
    df["completeness_pct"] = df["valid_days"] / df["days_in_year"] * 100.0
    df["who_level"] = df["annual_mean"].map(who_level)

    result = df.set_index(["city_id", "year"])
    return result[COLUMNS]