#!/bin/bash
mkdir -p /srv/racedb_secrets
aws s3 cp --recursive s3://${BUCKET}/racedb_secrets/ /srv/racedb_secrets/
S3_PRIVATE_BUCKET=`cat /srv/racedb_secrets/secrets.py | grep S3_PRIVATE_BUCKET | awk -F"'" '{print $2}'`
mkdir -p /pv/traefik
chmod 777 /pv/traefik
aws s3 cp s3://${S3_PRIVATE_BUCKET}/traefik/acme.json /pv/traefik/
chown 65532:65532 /pv/traefik/acme.json
chmod 600 /pv/traefik/acme.json
kubectl create secret generic racedb-aws --from-literal=traefik_backup_path="s3://${S3_PRIVATE_BUCKET}/traefik/acme.json"