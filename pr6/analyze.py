"""Аналіз вимірювань ПР6: енергія на одиницю R і SCI.

Запуск з папки pr6:  python analyze.py
Читає results/measurements_local.csv і, якщо є, результати
GitHub Actions: results/measurements_ci.csv, ecoci_ci.csv.
Записує results/summary.csv і reports/figures/energy_sci.png
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
FIG = ROOT / "reports" / "figures"

# ---------- Параметри SCI: перевірте й заповніть ----------
# Вуглецева інтенсивність мережі I, гCO2e/кВт·год (Ember,
# Yearly Electricity Data 2026, через Our World in Data)
I_LOCAL = 250.47    # Україна, 2022 р. (останній наявний)
I_CI = 458.29       # світ, 2025 р. (регіон раннера невідомий)
# Втілені викиди ноутбука TE, кгCO2e — з PCF-звіту
# виробника: повний слід мінус етап використання.
# Приклад: Dell Latitude 7450 (2024): 109 − 18 = 91.
TE_LAPTOP_KG = 91.0    # ← замініть даними свого ноутбука
EL_LAPTOP_YEARS = 4    # очікуваний строк служби, роки
# Раннер GitHub: сервер AMD EPYC 7763, 1151,7 кгCO2e
# (Boavizta, як у коді Eco CI); частка — vCPU зі 128
RUNNER_VCPU = 4     # публічний репозиторій; приватний — 2
TE_RUNNER_G = 1151.7e3 * RUNNER_VCPU / 128
EL_RUNNER_YEARS = 4

J_PER_KWH = 3.6e6
YEAR_S = 365 * 24 * 3600
# квантиль t(0,975) для n − 1 ступенів вільності
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776,
        5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}


def ci95(s: pd.Series) -> float:
    """Півширина 95 % довірчого інтервалу (формула 5)."""
    n = len(s)
    if n < 2:
        return float("nan")
    return T975.get(n - 1, 1.96) * s.std(ddof=1) / n ** 0.5


def codecarbon_rows(env: str) -> pd.DataFrame:
    f = RES / f"measurements_{env}.csv"
    if not f.exists():
        return pd.DataFrame()
    m = pd.read_csv(f)
    m["E_J"] = m["energy_kwh"] * J_PER_KWH
    m["P_W"] = m["E_J"] / m["duration_s"]          # (4)
    idle = m[m["label"] == "idle"]
    if len(idle):
        print(f"[{env} · CodeCarbon] простій: "
              f"{idle['P_W'].mean():.2f} Вт; режим CPU "
              f"{idle['cpu_mode'].iloc[0]}, "
              f"TDP {idle['tdp_w'].iloc[0]} Вт")
    run = m[m["label"] != "idle"].copy()
    run["E_R_J"] = run["E_J"] / run["iterations"]   # (3)
    run["t_R_s"] = run["duration_s"] / run["iterations"]
    run["source"] = f"{env} · CodeCarbon"
    return run


def ecoci_rows() -> pd.DataFrame:
    """Eco CI міряє крок цілком: ділимо на кількість
    повторів у кроці (з measurements_ci.csv) + 1 розігрів."""
    f = RES / "ecoci_ci.csv"
    c = RES / "measurements_ci.csv"
    if not (f.exists() and c.exists()):
        return pd.DataFrame()
    e = pd.read_csv(f)
    e["P_W"] = e["energy_j"] / e["time_s"]
    idle = e[e["label"] == "idle"]
    if len(idle):
        print(f"[ci · Eco CI] простій: "
              f"{idle['P_W'].mean():.2f} Вт")
    k = pd.read_csv(c).groupby("label")["iterations"].sum()
    e = e[e["label"].isin(k.index)
          & (e["label"] != "idle")].copy()
    e["iterations"] = e["label"].map(k) + 1
    e["E_R_J"] = e["energy_j"] / e["iterations"]
    e["t_R_s"] = e["time_s"] / e["iterations"]
    e["source"] = "ci · Eco CI"
    return e


def summarize(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (src, lab), g in data.groupby(["source", "label"],
                                      sort=False):
        local = src.startswith("local")
        e_r, t_r = g["E_R_J"].mean(), g["t_R_s"].mean()
        i = I_LOCAL if local else I_CI
        te_g = TE_LAPTOP_KG * 1000 if local else TE_RUNNER_G
        el = EL_LAPTOP_YEARS if local else EL_RUNNER_YEARS
        o = e_r / J_PER_KWH * i * 1000             # (8), мг
        m = te_g * t_r / (el * YEAR_S) * 1000      # (9), мг
        rows.append({
            "source": src, "label": lab, "n": len(g),
            "E_R_J": round(e_r, 3),
            "E_R_ci95": round(ci95(g["E_R_J"]), 3),
            "t_R_s": round(t_r, 4),
            "P_W": round(g["P_W"].mean(), 2),
            "O_mg": round(o, 4), "M_mg": round(m, 4),
            "SCI_mg": round(o + m, 4)})
    return pd.DataFrame(rows)


def compare(s: pd.DataFrame) -> None:
    print("\nПорівняння з базовою версією:")
    for src, g in s.groupby("source", sort=False):
        g = g.set_index("label")
        if "baseline" not in g.index:
            continue
        b = g.loc["baseline"]
        for v in ("optimized", "variant"):
            if v not in g.index:
                continue
            x = g.loc[v]
            saving = (1 - x.E_R_J / b.E_R_J) * 100     # (6)
            print(f"  {src} | {v}:\n"
                  f"    економія енергії {saving:.1f} %, "
                  f"прискорення {b.t_R_s / x.t_R_s:.1f}×, "
                  f"SCI {b.SCI_mg:.3f} → {x.SCI_mg:.4f} мг")


def plot(s: pd.DataFrame) -> None:
    labs = [x for x in ("baseline", "optimized", "variant")
            if x in set(s["label"])]
    srcs = list(dict.fromkeys(s["source"]))
    colors = ["#1E2761", "#B8912F", "#6B8F71"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    w = 0.8 / len(srcs)
    for j, src in enumerate(srcs):
        g = s[s["source"] == src].set_index("label")
        pos = [i for i, lab in enumerate(labs)
               if lab in g.index]
        sel = [labs[i] for i in pos]
        a1.bar([i + j * w for i in pos],
               g.loc[sel, "E_R_J"], w,
               yerr=g.loc[sel, "E_R_ci95"].fillna(0),
               capsize=3, label=src, color=colors[j % 3])
    a1.set_yscale("log")
    a1.set_xticks([i + w * (len(srcs) - 1) / 2
                   for i in range(len(labs))], labs)
    a1.set_ylabel("Енергія на R, Дж (лог. шкала)")
    a1.set_title("Енергія на один розрахунок індикаторів")
    a1.legend(fontsize=8)
    a1.grid(axis="y", alpha=0.3)
    t = s[s["label"].isin(labs)]
    names = [f"{r.source} · {r.label}"
             for r in t.itertuples()]
    a2.barh(names, t["O_mg"], color="#1E2761",
            label="O = E·I (операційні)")
    a2.barh(names, t["M_mg"], left=t["O_mg"],
            color="#B8912F", label="M (втілені)")
    a2.set_xlabel("SCI на R, мг CO₂e")
    a2.set_title("SCI = E·I + M на одиницю R")
    a2.tick_params(axis="y", labelsize=7)
    a2.invert_yaxis()
    a2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "energy_sci.png", dpi=150)


def main() -> None:
    parts = [p for p in (codecarbon_rows("local"),
                         codecarbon_rows("ci"), ecoci_rows())
             if len(p)]
    if not parts:
        raise SystemExit("Немає даних: measure.py run …")
    data = pd.concat(parts, ignore_index=True)
    s = summarize(data)
    pd.set_option("display.width", 140)
    print("\nЕнергія і SCI на функціональну одиницю R:")
    print(s.to_string(index=False))
    compare(s)
    RES.mkdir(exist_ok=True)
    s.to_csv(RES / "summary.csv", index=False)
    FIG.mkdir(parents=True, exist_ok=True)
    plot(s)
    print("\nЗбережено: results/summary.csv, "
          "reports/figures/energy_sci.png")


if __name__ == "__main__":
    main()
