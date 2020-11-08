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
apk add docker-compose mysql-client py-pip
/usr/bin/pip3 install awscli
aws s3 cp ${RACEDB_DB_BACKUP} .
echo "GRANT ALL PRIVILEGES ON *.* TO 'racedb'@'%';" | mysql -h mariadb -u root -pCHANGEME
echo "FLUSH PRIVILEGES;" | mysql -h mariadb -u root -pCHANGEME
zcat ./racedb.latest.sql.gz | mysql -h mariadb -u racedb -pCHANGEME racedb
MARIADB_IP=`grep mariadb /etc/hosts | awk '{print $1}'`
sed -i s/MARIADB_IP/$MARIADB_IP/g deploy/minimal/docker-compose-min.yml
cp racedb/secrets.py.sample racedb/secrets.py
cd deploy/minimal
docker-compose -f ./docker-compose-min.yml up -d
