"""Збирає результати Eco CI у results/ecoci_ci.csv.

Викликається у workflow: дані кроків передаються через змінні
середовища ECO_J_<МІТКА> = JSON, який повертає get-measurement.
"""
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "ecoci_ci.csv"
# JSON кожного кроку містить і всі попередні кроки,
# тому збираємо в словник за міткою (без повторів)
found = {}
for key, value in sorted(os.environ.items()):
    if not key.startswith("ECO_J_") or not value.strip():
        continue
    for step in json.loads(value).get("steps", []):
        found[step["label"]] = {
            "label": step["label"],
            "energy_j": float(step["energy_joules"]),
            "power_w": float(step["power_avg_watts"]),
            "time_s": float(step["time"]),
            "cpu_pct": float(step["cpu_avg_percent"]),
        }
rows = list(found.values())
OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=[
        "label", "energy_j", "power_w", "time_s", "cpu_pct"])
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(f"{r['label']:>10}: {r['energy_j']:9.1f} Дж за "
          f"{r['time_s']:6.1f} с ({r['power_w']:.2f} Вт)")
