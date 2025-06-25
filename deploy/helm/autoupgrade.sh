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
SLACK_GITLAB_WEBHOOK=$(cat /root/SLACK_GITLAB_WEBHOOK)
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

# upgrade if needed
if [ "$CURRENT_TAG" != "$LATEST_TAG" ]; then

  echo "[INFO] Pulling repo"
  if ! runuser -l ubuntu -c "cd /srv/racedb && git reset --hard && git clean -fd && git pull"; then
    # curl -sS -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"❌ Failed to update helm chart repo before deployment\"}" \
    #   "$SLACK_GITLAB_WEBHOOK"
    echo "[ERROR] Failed to pull repo"
    exit 1
  fi

  echo "[INFO] Deploying new tag: $LATEST_TAG to RRW"
  if ./upgrade.sh racedb values-rrw.yaml $LATEST_TAG; then

    # curl -sS -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"✅ Successfully upgraded *RRW* to *${LATEST_TAG}*\"}" \
    #   "$SLACK_GITLAB_WEBHOOK"
    echo "[INFO] Successfully upgraded RRW to ${LATEST_TAG}"

  else
    # curl -sS -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"❌ Failed to upgrade *RRW* to *${LATEST_TAG}*\"}" \
    #   "$SLACK_GITLAB_WEBHOOK"
    echo "[ERROR] Failed to upgrade RRW to ${LATEST_TAG}"
    exit 1
  fi

  echo "[INFO] Deploying new tag: $LATEST_TAG to racedbdev"
  if ! ./upgrade.sh racedbdev values-racedb.yaml $LATEST_TAG; then
    # curl -sS -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"❌ Failed to upgrade *racedbdev* to *${LATEST_TAG}*\"}" \
    #   "$SLACK_GITLAB_WEBHOOK"
    echo "[ERROR] Failed to upgrade racedbdev to ${LATEST_TAG}"
    exit 1
  fi

  echo "INFO: Deploying alloy"
  cd ../alloy
  if ! ./deploy.sh ; then

    # curl -sS -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"❌ Failed to deploy *Alloy*" \
    #   "$SLACK_GITLAB_WEBHOOK"
    # exit 1
    echo "[ERROR] Failed to deploy Alloy"
  fi

else

  echo "[INFO] RRW already running the latest tag: $CURRENT_TAG"

fi
