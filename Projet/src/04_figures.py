"""Figures du rapport (PNG dans report/figures/), a partir de la table gold des athletes.

Usage : python src/04_figures.py local_out/gold/running/athletes.parquet report/figures
Palette : slot 1 bleu, slot 2 orange (palette de reference dataviz, mode clair).
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update(
    {"font.family": "DejaVu Sans", "font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE}
)

a = pd.read_parquet(SRC)

# --- Figure 1 : nuage de points + vitesse par quartile de frequence -----------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.5, 1]})
for g, color, label in (("M", BLUE, "Hommes (149)"), ("F", ORANGE, "Femmes (27)")):
    d = a[a.gender == g]
    ax1.scatter(d.n_sessions, d.avg_speed_kmh, s=22, color=color, edgecolor=SURFACE, linewidth=1.2,
                alpha=0.9, label=label)
slope, icpt = np.polyfit(a.n_sessions, a.avg_speed_kmh, 1)
xs = np.array([a.n_sessions.min(), a.n_sessions.max()])
ax1.plot(xs, slope * xs + icpt, color=INK2, linewidth=1.5, linestyle="--")
ax1.text(272, 6.3, "tendance (pointillés) :\n+0,43 km/h pour 100 sessions", ha="right",
         va="bottom", color=INK2, fontsize=7.5)
ax1.set_xlabel("Sessions sur l'année (fréquence)")
ax1.set_ylabel("Vitesse moyenne (km/h)")
ax1.set_title("Un athlète = un point (n = 176)", loc="left", color=INK, fontsize=9)
ax1.legend(frameon=False, loc="upper left", fontsize=7.5)
ax1.grid(color=GRID, linewidth=0.6)
ax1.set_axisbelow(True)

q = a.groupby("freq_quartile").agg(n=("n_sessions", "mean"), v=("avg_speed_kmh", "mean"))
bars = ax2.bar(q.index.astype(str), q.v, color=BLUE, width=0.62)
for b, v in zip(bars, q.v):
    ax2.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}".replace(".", ","), ha="center", color=INK, fontsize=8)
ax2.set_xticks(range(4), [f"Q{i}\n({int(n)} sess.)" for i, n in zip(q.index, q.n)])
ax2.set_ylim(0, 13)
ax2.set_ylabel("Vitesse moyenne (km/h)")
ax2.set_title("Par quartile de fréquence", loc="left", color=INK, fontsize=9)
ax2.grid(axis="y", color=GRID, linewidth=0.6)
ax2.set_axisbelow(True)
for ax in (ax1, ax2):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/fig1_resultats.png", dpi=200)
plt.close(fig)

# --- Figure 2 : schema du pipeline ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.4, 1.9))
ax.set_xlim(0, 100)
ax.set_ylim(0, 26)
ax.axis("off")
boxes = [
    (1, "CSV brut\n65 880 lignes\n4,5 Mo", "#eceae4"),
    (21, "BRONZE (S3)\nbronze/running/\ncsv inchangé", "#f1dcc6"),
    (41, "SILVER (S3, Spark)\ntypage, qualité,\nflags repos/aberrant", "#d5d8dd"),
    (61, "GOLD (S3, SparkSQL)\n1 ligne / athlète\nquartiles, corrélations", "#f4e6a8"),
    (81, "VÉRIFICATION\npandas indépendant\n(depuis le CSV brut)", "#cfe3d4"),
]
for x, text, color in boxes:
    ax.add_patch(FancyBboxPatch((x, 5), 17.5, 16, boxstyle="round,pad=0.3,rounding_size=1.2",
                                facecolor=color, edgecolor=GRID, linewidth=1))
    ax.text(x + 8.75, 13, text, ha="center", va="center", fontsize=6.9, color=INK)
for x in (18.8, 38.8, 58.8, 78.8):
    ax.annotate("", xy=(x + 2.2, 13), xytext=(x, 13),
                arrowprops={"arrowstyle": "->", "color": INK2, "linewidth": 1.2})
captions = {
    1: "aws s3 cp\n(lab 03)",
    21: "dépôt S3\n(lab 03)",
    41: "01_bronze_to_silver\n(labs 06-07)",
    61: "02_silver_to_gold\n(lab 07)",
    81: "03_verify_pandas\n(sans Spark)",
}
for x, cap in captions.items():
    ax.text(x, 3.5, cap, fontsize=6.3, color=INK2, va="top")
fig.savefig(f"{OUT}/fig2_pipeline.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("figures ecrites dans", OUT)
