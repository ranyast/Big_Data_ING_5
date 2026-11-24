"""Session Spark : S3 Onyxia par defaut (meme config que le lab 07),
ou mode local si LOCAL_RUN=1 (tests sans Onyxia, fichiers dans ./local_out).
"""
import os

from pyspark.sql import SparkSession

LOCAL = os.environ.get("LOCAL_RUN") == "1"

if LOCAL:
    _root = os.path.abspath("local_out")
    RAW = os.path.abspath("data/running_data_france_final.csv")
    SILVER = f"{_root}/silver/running/sessions.parquet"
    GOLD_ATHLETES = f"{_root}/gold/running/athletes.parquet"
    GOLD_QUARTILES = f"{_root}/gold/running/frequency_quartiles.parquet"
    GOLD_CORR = f"{_root}/gold/running/correlations.parquet"
else:
    BUCKET = os.environ["LAB_BUCKET_NAME"]
    RAW = f"s3a://{BUCKET}/bronze/running/running_data_france_final.csv"
    SILVER = f"s3a://{BUCKET}/silver/running/sessions.parquet"
    GOLD_ATHLETES = f"s3a://{BUCKET}/gold/running/athletes.parquet"
    GOLD_QUARTILES = f"s3a://{BUCKET}/gold/running/frequency_quartiles.parquet"
    GOLD_CORR = f"s3a://{BUCKET}/gold/running/correlations.parquet"


def save(df, path: str) -> None:
    """Ecrit un DataFrame Spark en parquet. En local sous Windows, Spark ne sait pas ecrire
    sans winutils : on passe par pandas (test uniquement, Onyxia utilise l'ecriture Spark)."""
    if LOCAL:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.toPandas().to_parquet(path, index=False)
    else:
        df.write.mode("overwrite").parquet(path)


def load(spark: SparkSession, path: str):
    return spark.read.parquet(path)


def get_spark(name: str) -> SparkSession:
    builder = SparkSession.builder.appName(name)
    if LOCAL:
        os.environ.setdefault("HADOOP_HOME", os.path.abspath("local_out/hadoop"))
        os.makedirs(os.environ["HADOOP_HOME"] + "/bin", exist_ok=True)
        return builder.master("local[*]").config("spark.ui.enabled", "false").getOrCreate()
    return (
        builder.config("spark.hadoop.fs.s3a.endpoint", f"https://{os.environ['AWS_S3_ENDPOINT']}")
        .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"])
        .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"])
        .config("spark.hadoop.fs.s3a.session.token", os.environ.get("AWS_SESSION_TOKEN", ""))
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider",
        )
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )
