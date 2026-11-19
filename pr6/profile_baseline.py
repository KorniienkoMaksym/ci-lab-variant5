"""Профілювання базової версії (варіант 7).

Запуск з папки pr6:  python profile_baseline.py
Показує 15 функцій з найбільшим сукупним часом (cumtime).
"""
import cProfile
import pstats

from bench.baseline import compute_indicators

cProfile.run("compute_indicators()", "prof.out")
pstats.Stats("prof.out").sort_stats("cumtime").print_stats(15)
