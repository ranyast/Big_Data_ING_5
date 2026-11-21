#!/bin/sh
# Depose le CSV brut dans la couche bronze du bucket Onyxia (lab 03).
set -e
aws s3 --profile default cp data/running_data_france_final.csv \
  "s3://$LAB_BUCKET_NAME/bronze/running/running_data_france_final.csv"
aws s3 --profile default ls "s3://$LAB_BUCKET_NAME/bronze/running/"
