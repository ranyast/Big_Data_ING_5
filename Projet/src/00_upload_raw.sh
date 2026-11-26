#!/bin/sh
# Depose le CSV brut dans la couche bronze du bucket Onyxia (lab 03).
# Utilise les identifiants temporaires d'Onyxia (variables AWS_*) et le endpoint explicite,
# sans dependre d'un profil `default` dans ~/.aws.
set -e
unset AWS_PROFILE
EP="https://$AWS_S3_ENDPOINT"
aws s3 cp data/running_data_france_final.csv \
  "s3://$LAB_BUCKET_NAME/bronze/running/running_data_france_final.csv" --endpoint-url "$EP"
aws s3 ls "s3://$LAB_BUCKET_NAME/bronze/running/" --endpoint-url "$EP"
