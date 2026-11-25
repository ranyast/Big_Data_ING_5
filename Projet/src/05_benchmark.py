"""Mesures pour le rapport : pandas vs Spark (local[*]) sur l'agregation par athlete,
au volume du dataset (x1) et a un dataset 100 fois plus gros (x100).

Le dataset x100 est fabrique en repliquant le CSV 100 fois avec des identifiants d'athletes
decales (la structure et la distribution restent celles des vraies donnees).
Resultats : temps en secondes (mediane de 3 essais), machine locale, pas le cluster.

Usage : LOCAL_RUN=1 python src/05_benchmark.py data/running_data_france_final.csv <dossier_temp>
"""
import os
import statistics
import sys
import time

import pandas as pd

SRC, TMP = sys.argv[1], sys.argv[2]
os.makedirs(TMP, exist_ok=True)


def make_scaled(factor: int) -> str:
    path = os.path.join(TMP, f"running_x{factor}.csv")
    if not os.path.exists(path):
        base = pd.read_csv(SRC)
        step = int(base.athlete.max()) + 1
        parts = []
        for i in range(factor):
            part = base.copy()
            part["athlete"] = part["athlete"] + i * step
            parts.append(part)
        pd.concat(parts).to_csv(path, index=False)
    return path


def run_pandas(path: str) -> int:
    d = pd.read_csv(path)
    s = d[d.distance > 0].copy()
    s["speed"] = s.distance / (s.duration / 60)
    s = s[(s.speed >= 3) & (s.speed <= 25)]
    a = s.groupby("athlete").agg(n=("speed", "size"), km=("distance", "sum"), mn=("duration", "sum"))
    a["speed"] = a.km / (a.mn / 60)
    a["n"].corr(a["speed"], method="spearman")
    return len(a)


def run_spark(spark, path: str) -> int:
    from pyspark.sql import functions as F

    d = spark.read.csv(path, header=True, inferSchema=True)
    s = d.filter("distance > 0").withColumn("speed", F.col("distance") / (F.col("duration") / 60))
    s = s.filter((F.col("speed") >= 3) & (F.col("speed") <= 25))
    a = s.groupBy("athlete").agg(
        F.count("*").alias("n"), F.sum("distance").alias("km"), F.sum("duration").alias("mn")
    )
    a = a.withColumn("speed", F.col("km") / (F.col("mn") / 60))
    a.stat.corr("n", "speed")
    return a.count()


def timed(fn, *args, repeats=3):
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        n = fn(*args)
        times.append(time.perf_counter() - t0)
    return statistics.median(times), n


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from common import get_spark

    t0 = time.perf_counter()
    spark = get_spark("benchmark")
    spark.sparkContext.setLogLevel("ERROR")
    print(f"demarrage Spark : {time.perf_counter() - t0:.1f} s")
    print("facteur | lignes | taille CSV | pandas (s) | Spark local (s) | athletes")
    for factor in (1, 100):
        path = SRC if factor == 1 else make_scaled(factor)
        rows = sum(1 for _ in open(path, "rb")) - 1
        mb = os.path.getsize(path) / 1e6
        t_pd, n_pd = timed(run_pandas, path)
        t_sp, n_sp = timed(run_spark, spark, path)
        assert n_pd == n_sp, (n_pd, n_sp)
        print(f"x{factor} | {rows} | {mb:.1f} Mo | {t_pd:.2f} | {t_sp:.2f} | {n_pd}")
    spark.stop()
