"""Mesure de l'alternative DuckDB (lab 04) sur la meme agregation que 05_benchmark.py :
filtre des sessions, vitesse, agregat par athlete, correlations de Pearson et de Spearman.

Memes donnees que 05_benchmark.py : x1 (CSV reel) et x100 (CSV replique 100 fois avec des
identifiants d'athletes decales). Temps en secondes, mediane de 3 essais.
Le fichier x100 (~460 Mo) est cree dans <dossier_temp> : le supprimer ensuite.

Usage Onyxia : uv run --with duckdb --with pandas python src/06_benchmark_duckdb.py \
                   data/running_data_france_final.csv /tmp/bench
"""
import os
import statistics
import sys
import time

import duckdb
import pandas as pd

SRC, TMP = sys.argv[1], sys.argv[2]
os.makedirs(TMP, exist_ok=True)

QUERY = """
WITH s AS (
    SELECT athlete, distance, duration, distance / (duration / 60) AS speed
    FROM read_csv(?, header = true)
    WHERE distance > 0 AND duration > 0
),
a AS (
    SELECT athlete, count(*) AS n, sum(distance) / (sum(duration) / 60) AS speed
    FROM s WHERE speed BETWEEN 3 AND 25
    GROUP BY athlete
),
r AS (  -- rang moyen en cas d'ex-aequo, comme pandas et 02_silver_to_gold.py
    SELECT n, speed,
           rank() OVER (ORDER BY n) + (count(*) OVER (PARTITION BY n) - 1) / 2 AS rn,
           rank() OVER (ORDER BY speed) + (count(*) OVER (PARTITION BY speed) - 1) / 2 AS rs
    FROM a
)
SELECT count(*) AS athletes, corr(n, speed) AS pearson, corr(rn, rs) AS spearman FROM r
"""


def make_scaled(factor: int) -> str:
    """Identique a 05_benchmark.py : ecriture par morceaux, memoire constante."""
    path = os.path.join(TMP, f"running_x{factor}.csv")
    if not os.path.exists(path):
        base = pd.read_csv(SRC)
        step = int(base.athlete.max()) + 1
        with open(path, "w", newline="") as f:
            for i in range(factor):
                part = base.copy()
                part["athlete"] = part["athlete"] + i * step
                part.to_csv(f, header=(i == 0), index=False)
    return path


def run_duckdb(path: str):
    con = duckdb.connect()  # base en memoire, aucune donnee chargee a l'avance
    try:
        return con.execute(QUERY, [path]).fetchone()
    finally:
        con.close()


if __name__ == "__main__":
    print(f"duckdb {duckdb.__version__}")
    print("facteur | lignes | taille CSV | DuckDB (s) | athletes | pearson | spearman")
    for factor in (1, 100):
        path = SRC if factor == 1 else make_scaled(factor)
        with open(path, "rb") as f:
            rows = sum(1 for _ in f) - 1
        mb = os.path.getsize(path) / 1e6
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            n, pearson, spearman = run_duckdb(path)
            times.append(time.perf_counter() - t0)
        print(f"x{factor} | {rows} | {mb:.1f} Mo | {statistics.median(times):.2f} | {n} | "
              f"{pearson:.4f} | {spearman:.4f}")
