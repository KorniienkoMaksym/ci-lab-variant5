"""Вимірювання енергоспоживання навантаження ПР6 (CodeCarbon).

Команди (запускати з папки pr6):
  python measure.py check           чим вимірює CodeCarbon
  python measure.py verify          версії дають той самий
                                    результат?
  python measure.py idle            простій (фон)
  python measure.py run baseline    базова версія
  python measure.py run optimized   оптимізована версія
  python measure.py run variant     версія за варіантом

Результати дописуються у results/measurements_<env>.csv,
де env = local (ваш комп'ютер) або ci (GitHub Actions).
"""
import argparse
import csv
import importlib
import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from codecarbon import OfflineEmissionsTracker

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from bench.common import normalize  # noqa: E402

# Вуглецева інтенсивність мережі України, гCO2e/кВт·год:
# Ember, Yearly Electricity Data (2026), 2022 р. — останній
# рік, наявний для України (через Our World in Data)
GRID_UA = 250.47

IN_CI = os.getenv("GITHUB_ACTIONS") == "true"
ENV = "ci" if IN_CI else "local"
OUT = ROOT / "results" / f"measurements_{ENV}.csv"
FIELDS = ["timestamp", "env", "label", "repeat",
          "iterations", "duration_s", "energy_kwh",
          "cpu_energy_kwh", "ram_energy_kwh", "cpu_power_w",
          "ram_power_w", "cpu_mode", "cpu_model", "tdp_w",
          "os"]
MEASURED = ("intel_rapl", "windows_emi",
            "apple_powermetrics", "intel_power_gadget")


def make_tracker() -> OfflineEmissionsTracker:
    """Трекер без мережі: нікуди не надсилає дані й не
    визначає місце за IP; інтенсивність I задаємо самі."""
    return OfflineEmissionsTracker(
        country_iso_code="UKR",
        force_carbon_intensity_g_co2e_kwh=GRID_UA,
        measure_power_secs=1,      # опитування щосекунди
        tracking_mode="machine",   # увесь комп'ютер
        save_to_file=False,        # CSV пишемо самі
        log_level="error",
        allow_multiple_runs=True,
    )


def hw_info(tracker) -> dict:
    """Як CodeCarbon отримує потужність процесора."""
    info = {"cpu_mode": "?", "cpu_model": "?", "tdp_w": ""}
    for h in getattr(tracker, "_hardware", []):
        name = type(h).__name__
        if name == "CPU":
            info["cpu_mode"] = getattr(h, "_mode", "?")
            info["cpu_model"] = getattr(h, "_model", "?")
            info["tdp_w"] = getattr(h, "_tdp", "")
        elif name == "AppleSiliconChip":
            info["cpu_mode"] = "apple_powermetrics"
    return info


def save(rows: list) -> None:
    OUT.parent.mkdir(exist_ok=True)
    new = not OUT.exists()
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)


def measure_block(label, repeat, work, min_s) -> dict:
    """Один вимір: повторюємо роботу, доки не мине min_s
    секунд, і рахуємо повтори k (функціональні одиниці)."""
    tracker = make_tracker()
    tracker.start()
    info = hw_info(tracker)
    t0 = time.perf_counter()
    k = 0
    while True:
        if work is None:
            time.sleep(0.2)        # простій: нічого не робимо
        else:
            work()
            k += 1
        if time.perf_counter() - t0 >= min_s:
            break
    duration = time.perf_counter() - t0
    tracker.stop()
    d = tracker.final_emissions_data
    e_j = d.energy_consumed * 3.6e6
    print(f"{label:>10} #{repeat}: {k:>4} повт. за "
          f"{duration:5.1f} с, E = {e_j:7.1f} Дж, "
          f"P = {e_j / duration:5.1f} Вт")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "env": ENV, "label": label, "repeat": repeat,
        "iterations": k, "duration_s": round(duration, 3),
        "energy_kwh": d.energy_consumed,
        "cpu_energy_kwh": d.cpu_energy,
        "ram_energy_kwh": d.ram_energy,
        "cpu_power_w": round(d.cpu_power, 3),
        "ram_power_w": round(d.ram_power, 3),
        "os": platform.platform(terse=True), **info,
    }


def load(module: str, func: str = "compute_indicators"):
    return getattr(importlib.import_module(f"bench.{module}"),
                   func)


def cmd_check(_args) -> None:
    tracker = make_tracker()
    tracker.start()
    info = hw_info(tracker)
    time.sleep(3)
    tracker.stop()
    ram_w = tracker.final_emissions_data.ram_power
    how = ("ВИМІР апаратними лічильниками"
           if info["cpu_mode"] in MEASURED
           else "ОЦІНКА за завантаженням і TDP")
    print("Середовище: ", ENV, "|",
          platform.platform(terse=True))
    print("Процесор:   ", info["cpu_model"])
    print("Спосіб CPU: ", info["cpu_mode"], "→", how)
    print("TDP:        ", info["tdp_w"], "Вт (для оцінки)")
    print("RAM:        ", round(ram_w, 1),
          "Вт (завжди оцінка)")


def cmd_verify(_args) -> None:
    import pandas as pd
    ref = normalize(load("baseline")())
    cols = ["city_id", "year", "annual_mean", "valid_days",
            "days_over_15", "completeness_pct", "who_level"]
    print(ref[cols].round(2).to_string(index=False))
    for name in ("optimized", "variant"):
        other = normalize(load(name)())
        pd.testing.assert_frame_equal(ref, other,
                                      check_dtype=False)
        print(f"OK: {name} дає той самий результат")


def cmd_idle(args) -> None:
    save([measure_block("idle", i + 1, None, args.seconds)
          for i in range(args.repeat)])


def cmd_run(args) -> None:
    work = load(args.version, args.func)
    if not args.no_warmup:
        work()           # «розігрів»: імпорти, кеш файлів ОС
    rows = [measure_block(args.version, i + 1, work,
                          args.seconds)
            for i in range(args.repeat)]
    save(rows)
    k = sum(r["iterations"] for r in rows)
    print(f"Разом повторів (R) для {args.version}: {k}")


def main() -> None:
    logging.getLogger("codecarbon").setLevel(logging.ERROR)
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(f=cmd_check)
    sub.add_parser("verify").set_defaults(f=cmd_verify)
    s = sub.add_parser("idle")
    s.add_argument("--seconds", type=float, default=20)
    s.add_argument("--repeat", type=int, default=3)
    s.set_defaults(f=cmd_idle)
    s = sub.add_parser("run")
    s.add_argument("version",
                   help="модуль з папки bench: baseline, "
                        "optimized, variant…")
    s.add_argument("--func", default="compute_indicators")
    s.add_argument("--seconds", type=float, default=20,
                   help="мінімальна тривалість виміру, с")
    s.add_argument("--repeat", type=int, default=5)
    s.add_argument("--no-warmup", action="store_true")
    s.set_defaults(f=cmd_run)
    args = p.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
