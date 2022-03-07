#!/bin/bash
# replace the dev database with the latest prod backup in S3

set -e
set -u

KUBECONFIG=/etc/rancher/k3s/k3s.yaml
DBHOST=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_HOST | awk '{print $3}' | awk -F"'" '{print $2}'`
DBPW=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_PASSWORD | awk '{print $3}' | awk -F"'" '{print $2}'`
DEVWEBPOD=`kubectl get pods | grep racedbdev-web | awk '{print $1}'`

aws s3 cp --quiet s3://racedb-private/database_backup/racedb.latest.sql.gz /tmp
gunzip /tmp/racedb.latest.sql.gz
cat /tmp/racedb.latest.sql | kubectl exec $DEVWEBPOD -- mysql -h $DBHOST -u racedbdev -p$DBPW racedbdev
rm -f /tmp/racedb.latest.sql
