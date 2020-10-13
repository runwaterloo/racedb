#!/bin/bash
mkdir -p /srv/racedb_secrets
aws s3 cp --recursive s3://${BUCKET}/racedb_secrets/ /srv/racedb_secrets/
kubectl apply -f ./racedb_yaml