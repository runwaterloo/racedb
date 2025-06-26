#!/bin/bash

set -euo pipefail

# log output to systemd journal
exec > >(systemd-cat -t racedb-autoupgrade) 2>&1

# prevent concurrent execution
exec 200>/var/lock/racedb-deploy.lock
flock -n 200 || { echo "WARNING: Another deployment is already running. Exiting."; exit 1; }

OWNER=runwaterloo
REPO=racedb
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
# move to directory
cd /srv/racedb/deploy/helm


LATEST_TAG=$(curl -s https://api.github.com/repos/$OWNER/$REPO/tags | jq -r '.[0].name')
if [ -z "$LATEST_TAG" ]; then
  echo "[ERROR] Failed to fetch latest tag from GitHub"
  exit 1
else
  echo "[INFO] Latest tag: $LATEST_TAG"
fi

# get current tag from deployment
CURRENT_TAG=$(kubectl get deployment racedb-web -o jsonpath="{.spec.template.spec.containers[*].image}" | awk -F":" '{print $2}')
echo "[INFO] Current tag: $CURRENT_TAG"

if [[ "$LATEST_TAG" == dev* ]]; then
  echo "[INFO] Latest tag is a dev tag. Only upgrading racedbdev if needed."
  CURRENT_DEV_TAG=$(kubectl get deployment racedbdev-web -o jsonpath="{.spec.template.spec.containers[*].image}" | awk -F":" '{print $2}')
  echo "[INFO] racedbdev current tag: $CURRENT_DEV_TAG"
  if [ "$CURRENT_DEV_TAG" != "$LATEST_TAG" ]; then
    echo "[INFO] Deploying dev tag: $LATEST_TAG to racedbdev"
    if ./upgrade.sh racedbdev values-racedb.yaml $LATEST_TAG; then
      echo "[INFO] Successfully upgraded racedbdev to ${LATEST_TAG}"
    else
      echo "[ERROR] Failed to upgrade racedbdev to ${LATEST_TAG}"
      exit 1
    fi
  else
    echo "[INFO] racedbdev already running the latest dev tag: $CURRENT_DEV_TAG"
  fi
else
  if [ "$CURRENT_TAG" != "$LATEST_TAG" ]; then
    echo "[INFO] Pulling repo"
    if ! runuser -l ubuntu -c "cd /srv/racedb && git reset --hard && git clean -fd && git pull"; then
      echo "[ERROR] Failed to pull repo"
      exit 1
    fi
    echo "[INFO] Deploying new tag: $LATEST_TAG to RRW"
    if ./upgrade.sh racedb values-rrw.yaml $LATEST_TAG; then
      echo "[INFO] Successfully upgraded RRW to ${LATEST_TAG}"
    else
      echo "[ERROR] Failed to upgrade RRW to ${LATEST_TAG}"
      exit 1
    fi
    echo "[INFO] Deploying new tag: $LATEST_TAG to racedbdev"
    if ! ./upgrade.sh racedbdev values-racedb.yaml $LATEST_TAG; then
      echo "[ERROR] Failed to upgrade racedbdev to ${LATEST_TAG}"
      exit 1
    fi
    echo "INFO: Deploying alloy"
    cd ../alloy
    if ! ./deploy.sh ; then
      echo "[ERROR] Failed to deploy Alloy"
    fi
  else
    echo "[INFO] RRW already running the latest tag: $CURRENT_TAG"
  fi
fi
