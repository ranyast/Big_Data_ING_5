"""Silver -> Gold : une ligne par athlete + reponse a la problematique (lab 07).

Frequence = nombre de sessions sur l'annee. Vitesse = km totaux / heures totales
(moyenne ponderee par la duree, pas moyenne des vitesses de chaque session).
"""
from pyspark.sql import Window
from pyspark.sql import functions as F

from common import GOLD_ATHLETES, GOLD_CORR, GOLD_QUARTILES, SILVER, get_spark, load, save

spark = get_spark("running-silver-to-gold")
load(spark, SILVER).createOrReplaceTempView("sessions")

athletes = spark.sql("""
    SELECT athlete_id,
           first(gender)     AS gender,
           first(age_group)  AS age_group,
           max(majors_count) AS majors_count,
           count(*)          AS days_observed,
           sum(CASE WHEN is_session AND NOT is_outlier THEN 1 ELSE 0 END) AS n_sessions,
           sum(CASE WHEN is_session AND NOT is_outlier THEN distance_km END) AS total_km,
           sum(CASE WHEN is_session AND NOT is_outlier THEN duration_min END) / 60 AS total_hours
    FROM sessions
    GROUP BY athlete_id
""")
# Athletes sans aucune session : pas de vitesse, exclus de l'analyse
athletes = (
    athletes.filter("n_sessions > 0")
    .withColumn("avg_speed_kmh", F.col("total_km") / F.col("total_hours"))
    .withColumn("sessions_per_week", F.col("n_sessions") / (F.col("days_observed") / 7))
    .withColumn("freq_quartile", F.ntile(4).over(Window.orderBy("n_sessions", "athlete_id")))
    .withColumn("speed_quartile", F.ntile(4).over(Window.orderBy("avg_speed_kmh", "athlete_id")))
)
save(athletes, GOLD_ATHLETES)
athletes.createOrReplaceTempView("athletes")

# Vitesse moyenne par quartile de frequence
quart = spark.sql("""
    SELECT freq_quartile, count(*) AS n_athletes,
           round(avg(n_sessions), 1)    AS avg_sessions,
           round(avg(avg_speed_kmh), 2) AS avg_speed_kmh
    FROM athletes GROUP BY freq_quartile ORDER BY freq_quartile
""")
quart.show()
save(quart, GOLD_QUARTILES)

# Correlations de Pearson et Spearman (Spearman = Pearson sur les rangs moyens)
def avg_rank(col):
    """Rang moyen en cas d'ex-aequo (comme pandas/scipy) : rank() + (nb_ex-aequo - 1) / 2."""
    return F.rank().over(Window.orderBy(col)) + (
        F.count(F.lit(1)).over(Window.partitionBy(col)) - 1
    ) / 2


ranked = athletes.select(
    avg_rank("n_sessions").alias("rank_n"), avg_rank("avg_speed_kmh").alias("rank_s")
)
pearson = athletes.stat.corr("n_sessions", "avg_speed_kmh")
spearman = ranked.stat.corr("rank_n", "rank_s")
# Recouvrement : parmi les 25 % les plus rapides, quelle part est aussi dans les 25 % les plus assidus ?
top = athletes.filter("speed_quartile = 4")
overlap = top.filter("freq_quartile = 4").count() / top.count()
corr = spark.sql(
    f"""SELECT 'pearson' AS metric, CAST({pearson} AS DOUBLE) AS value
        UNION ALL SELECT 'spearman', CAST({spearman} AS DOUBLE)
        UNION ALL SELECT 'top_speed_also_top_freq', CAST({overlap} AS DOUBLE)"""
)
corr.show(truncate=False)
save(corr, GOLD_CORR)
spark.stop()
