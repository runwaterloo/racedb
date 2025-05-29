#!/bin/bash

set -euo pipefail

# prevent concurrent execution
exec 200>/var/lock/racedb-deploy.lock
flock -n 200 || { echo "Another deployment is already running. Exiting."; exit 1; }

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
export PROJECT_ID=$(cat /root/PROJECT_ID)
export PERSONAL_ACCESS_TOKEN=$(cat /root/PERSONAL_ACCESS_TOKEN)
export SLACK_GITLAB_WEBHOOK=$(cat /root/SLACK_GITLAB_WEBHOOK)

# move to directory
cd /srv/racedb/deploy/helm

# get current tag from deployment
CURRENT_TAG=$(kubectl get deployment racedb-web -o jsonpath="{.spec.template.spec.containers[*].image}" | awk -F":" '{print $2}')
echo "Current tag: $CURRENT_TAG"

# get latest tag from gitlab
LATEST_TAG=$(curl -sS --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" \
  "https://gitlab.com/api/v4/projects/${PROJECT_ID}/repository/tags/" | jq -r '.[0].name' | awk -F"v" '{print $2}')
echo "Latest tag: ${LATEST_TAG}"

# upgrade if needed
if [ "$CURRENT_TAG" != "$LATEST_TAG" ]; then

  echo "Ensure gitlab.com SSH host key is known"
  runuser -l ubuntu -c "mkdir -p ~/.ssh && touch ~/.ssh/known_hosts && grep -q gitlab.com ~/.ssh/known_hosts || ssh-keyscan gitlab.com >> ~/.ssh/known_hosts"

  echo "Pulling repo"
  if ! runuser -l ubuntu -c "cd /srv/racedb && git reset --hard && git clean -fd && git pull"; then
    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to update helm chart repo before deployment\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    exit 1
  fi

  echo "Deploying new tag: $LATEST_TAG to RRW"
  if helm upgrade --install racedb . \
    --values values-rrw.yaml \
    --set image.tag="${LATEST_TAG}" \
    --wait --timeout 5m; then

    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"✅ Successfully upgraded *RRW* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"

  else
    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to upgrade *RRW* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    exit 1
  fi

  echo "Deploying new tag: $LATEST_TAG to racedbdev"
  if ! helm upgrade --install racedbdev . \
    --values values-racedb.yaml \
    --set image.tag="${LATEST_TAG}" \
    --wait --timeout 5m; then

    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to upgrade *racedbdev* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    exit 1
  fi

else
  echo "Already running the latest tag: $CURRENT_TAG"
fi
