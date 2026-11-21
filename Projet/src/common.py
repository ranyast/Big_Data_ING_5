"""Session Spark connectee au S3 Onyxia (meme config que le lab 07)."""
import os

from pyspark.sql import SparkSession

BUCKET = os.environ["LAB_BUCKET_NAME"]
RAW = f"s3a://{BUCKET}/bronze/running/running_data_france_final.csv"
SILVER = f"s3a://{BUCKET}/silver/running/sessions.parquet"
GOLD_ATHLETES = f"s3a://{BUCKET}/gold/running/athletes.parquet"
GOLD_QUARTILES = f"s3a://{BUCKET}/gold/running/frequency_quartiles.parquet"
GOLD_CORR = f"s3a://{BUCKET}/gold/running/correlations.parquet"


def get_spark(name: str) -> SparkSession:
    return (
        SparkSession.builder.appName(name)
        .config("spark.hadoop.fs.s3a.endpoint", f"https://{os.environ['AWS_S3_ENDPOINT']}")
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
