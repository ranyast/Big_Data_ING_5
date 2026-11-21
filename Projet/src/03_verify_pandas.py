"""Verification independante : recalcul des resultats gold avec pandas a partir du CSV brut
(sans Spark, sans passer par silver). A comparer avec la sortie de 02_silver_to_gold.py.

Usage : python src/03_verify_pandas.py data/running_data_france_final.csv
"""
import sys

import pandas as pd

d = pd.read_csv(sys.argv[1])
s = d[d.distance > 0].copy()
s["speed"] = s.distance / (s.duration / 60)
s = s[(s.speed >= 3) & (s.speed <= 25)]
a = s.groupby("athlete").agg(n=("speed", "size"), km=("distance", "sum"), mn=("duration", "sum"))
a["speed"] = a.km / (a.mn / 60)
print("athletes analyses :", len(a))
print("pearson  :", round(a.n.corr(a.speed), 4))
print("spearman :", round(a.n.corr(a.speed, method="spearman"), 4))
a["q"] = pd.qcut(a.n.rank(method="first"), 4, labels=[1, 2, 3, 4])
print(
    a.groupby("q", observed=True)
    .agg(n_athletes=("n", "size"), avg_sessions=("n", "mean"), avg_speed=("speed", "mean"))
    .round(2)
)
