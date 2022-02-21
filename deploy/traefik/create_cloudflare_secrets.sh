#!/bin/bash
#
# This assumes you have an S3 envar $BUCKET if on AWS
#
# YAML can be initially created as follows:
# kubectl create secret generic cloudflare-secrets --from-literal=apiToken=<api-token> --dry-run -o yaml > <FILE>
#
FILE=/srv/cloudflare_persistent/secrets.yaml
if [ -f "$FILE" ]; then  # this should be dev
    echo "Using existing $FILE to create Cloudflare secrets"
    kubectl apply -f $FILE
else  # this should be AWS
    echo "$FILE not found, restoring from S3"
    mkdir -p /srv/cloudflare_persistent
    aws s3 cp s3://${BUCKET}/cloudflare/secrets.yaml $FILE
    kubectl apply -f $FILE
    rm -rf /srv/cloudflare_persistent
fi
