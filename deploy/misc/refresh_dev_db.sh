#!/bin/bash
# replace the dev database with the latest prod backup in S3

set -e
set -u

KUBECONFIG=/etc/rancher/k3s/k3s.yaml
DEVDBHOST=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_HOST | awk '{print $3}' | awk -F"'" '{print $2}'`
DEVDBPW=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_PASSWORD | awk '{print $3}' | awk -F"'" '{print $2}'`
DEVWEBPOD=`kubectl get pods | grep racedbdev-web | awk '{print $1}'`
PRODDBHOST=`cat /srv/racedb_secrets/secrets.py | grep DB_HOST | awk '{print $3}' | awk -F"'" '{print $2}'`
PRODDBPW=`cat /srv/racedb_secrets/secrets.py | grep DB_PASSWORD | awk '{print $3}' | awk -F"'" '{print $2}'`
PRODWEBPOD=`kubectl get pods | grep racedb-web | awk '{print $1}'`
kubectl exec $PRODWEBPOD -c racedb -- mysqldump -h $PRODDBHOST -u racedb -p$PRODDBPW racedb > /tmp/dump.sql > /tmp/dump.sql
cat /tmp/dump.sql | kubectl exec -i $DEVWEBPOD -- mysql -h $DEVDBHOST -u racedbdev -p$DEVDBPW racedbdev
kubectl exec $DEVWEBPOD -- ./manage.py clear_cache
rm -f /tmp/dump.sql
