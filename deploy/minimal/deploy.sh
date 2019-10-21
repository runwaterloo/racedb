#!/bin/ash
#
# This is built to run in an alpine-based docker:dind container
# Adapt as necessary to run on a different platform
# The following environment variables must be set:
#
# AWS_ACCESS_KEY
# AWS_SECRET_ACCESS_KEY
# RACEDB_DB_BACKUP

echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
apk add awscli docker-compose
export PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)
mkdir ./db_restore
aws s3 cp ${RACEDB_DB_BACKUP} ./db_restore
sed -i s/CHANGEME/$PASSWORD/g racedb/secrets.py.sample
cd deploy/minimal
docker-compose -f ./docker-compose-min.yml up -d
