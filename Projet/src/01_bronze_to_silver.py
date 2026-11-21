"""Bronze -> Silver : nettoyage et typage (labs 06/07).

Regles de qualite appliquees (chaque compteur est affiche pour le rapport) :
  - colonne parasite `Unnamed: 0` supprimee (index pandas)
  - types : date, entiers, doubles ; `major` -> nombre de marathons majeurs
  - jour de repos = distance 0 et duree 0 (is_session = false)
  - incoherences distance/duree (un seul des deux a 0) rejetees
  - vitesse aberrante (< 3 ou > 25 km/h) marquee is_outlier, exclue de la vitesse
  - doublons (athlete, date) supprimes
"""
from pyspark.sql import functions as F

from common import RAW, SILVER, get_spark

SPEED_MIN, SPEED_MAX = 3.0, 25.0

spark = get_spark("running-bronze-to-silver")
raw = spark.read.csv(RAW, header=True, inferSchema=True)
print(f"[quality] lignes brutes : {raw.count()}")

df = raw.select(
    F.to_date("datetime").alias("session_date"),
    F.col("athlete").cast("int").alias("athlete_id"),
    F.col("distance").cast("double").alias("distance_km"),
    F.col("duration").cast("double").alias("duration_min"),
    "gender",
    "age_group",
    F.when(F.col("major").isNull() | (F.trim("major") == ""), 0)
    .otherwise(F.size(F.split("major", ",")))
    .alias("majors_count"),
)

key_cols = ["session_date", "athlete_id", "distance_km", "duration_min"]
n_null = df.count() - df.dropna(subset=key_cols).count()
df = df.dropna(subset=key_cols)
print(f"[quality] lignes avec cle/valeur nulle supprimees : {n_null}")

coherent = (F.col("distance_km") > 0) == (F.col("duration_min") > 0)
n_incoh = df.filter(~coherent).count()
df = df.filter(coherent)
print(f"[quality] incoherences distance/duree supprimees : {n_incoh}")

deduped = df.dropDuplicates(["athlete_id", "session_date"])
print(f"[quality] doublons (athlete, date) supprimes : {df.count() - deduped.count()}")
df = deduped

df = (
    df.withColumn("is_session", F.col("distance_km") > 0)
    .withColumn(
        "speed_kmh",
        F.when(F.col("is_session"), F.col("distance_km") / (F.col("duration_min") / 60)),
    )
    .withColumn(
        "is_outlier",
        F.col("is_session") & ((F.col("speed_kmh") < SPEED_MIN) | (F.col("speed_kmh") > SPEED_MAX)),
    )
)

print(f"[quality] jours de repos (distance=0) : {df.filter(~F.col('is_session')).count()}")
print(
    f"[quality] sessions aberrantes (vitesse hors [{SPEED_MIN},{SPEED_MAX}] km/h) : "
    f"{df.filter('is_outlier').count()}"
)
inactive = (
    df.groupBy("athlete_id")
    .agg(F.sum(F.col("is_session").cast("int")).alias("n"))
    .filter("n = 0")
    .count()
)
print(f"[quality] athletes jamais actifs : {inactive}")

df.write.mode("overwrite").parquet(SILVER)
print(f"[silver] {df.count()} lignes ecrites dans {SILVER}")
spark.stop()
