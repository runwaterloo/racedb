#!/bin/bash
# connect to the dev database

set -e
set -u

KUBECONFIG=/etc/rancher/k3s/k3s.yaml
DEVDBHOST=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_HOST | awk '{print $3}' | awk -F"'" '{print $2}'`
DEVDBPW=`cat /srv/racedb_secrets_dev/secrets.py | grep DB_PASSWORD | awk '{print $3}' | awk -F"'" '{print $2}'`
DEVWEBPOD=`kubectl get pods | grep racedbdev-web | awk '{print $1}'`
kubectl exec -it $DEVWEBPOD -- mysql -h $DEVDBHOST -u racedbdev -p$DEVDBPW racedbdev
