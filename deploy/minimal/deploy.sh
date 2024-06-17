#!/bin/ash
#
# This is built to run in an alpine-based docker:dind container
# Adapt as necessary to run on a different platform
# The following environment variables must be set:
#
# AWS_ACCESS_KEY
# AWS_SECRET_ACCESS_KEY
# RACEDB_DB_BACKUP

export WEBHOST=testing

echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
apk add docker-compose mysql-client py-pip
echo "GRANT ALL PRIVILEGES ON *.* TO 'racedb'@'%';" | mysql -h mariadb -u root -pCHANGEME
echo "FLUSH PRIVILEGES;" | mysql -h mariadb -u root -pCHANGEME
cp racedb/secrets.py.sample racedb/secrets.py
cd deploy/minimal
docker-compose -f ./docker-compose-min.yml up -d
