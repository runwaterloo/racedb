#!/bin/bash

set -euo pipefail

# log output to systemd journal
exec > >(systemd-cat -t racedb-upgrade) 2>&1

# prevent concurrent execution
exec 200>/var/lock/racedb-deploy.lock
flock -n 200 || { echo "WARNING: Another deployment is already running. Exiting."; exit 1; }

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
export PROJECT_ID=$(cat /root/PROJECT_ID)
export PERSONAL_ACCESS_TOKEN=$(cat /root/PERSONAL_ACCESS_TOKEN)
export SLACK_GITLAB_WEBHOOK=$(cat /root/SLACK_GITLAB_WEBHOOK)

# move to directory
cd /srv/racedb/deploy/helm

# pre-flight check
SHA_FILE="/tmp/latest_pipeline_sha.txt"
read latest_pipeline_status latest_pipeline_sha < <(curl -s --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" \
  "https://gitlab.com/api/v4/projects/${PROJECT_ID}/pipelines?per_page=1" | jq -r '.[0] | "\(.status) \(.sha[0:8])"')
if [ -f "$SHA_FILE" ] && grep -q "$latest_pipeline_sha" "$SHA_FILE"; then
  echo "INFO: SHA hasn't changed since last run ($latest_pipeline_sha), exiting."
  exit 0
elif [ "$latest_pipeline_status" = "success" ]; then
  echo "$latest_pipeline_sha" > "$SHA_FILE"
fi

# get current tag from deployment
CURRENT_TAG=$(kubectl get deployment racedb-web -o jsonpath="{.spec.template.spec.containers[*].image}" | awk -F":" '{print $2}')
echo "INFO: Current tag: $CURRENT_TAG"

# get latest tag from gitlab
LATEST_TAG=$(curl -sS --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" \
  "https://gitlab.com/api/v4/projects/${PROJECT_ID}/repository/tags/" | jq -r '.[0].name')
echo "INFO: Latest tag: ${LATEST_TAG}"

# upgrade if needed
if [ "$CURRENT_TAG" != "$LATEST_TAG" ]; then

  echo "INFO: Ensure gitlab.com SSH host key is known"
  runuser -l ubuntu -c "mkdir -p ~/.ssh && touch ~/.ssh/known_hosts && grep -q gitlab.com ~/.ssh/known_hosts || ssh-keyscan gitlab.com >> ~/.ssh/known_hosts"

  echo "INFO: Pulling repo"
  if ! runuser -l ubuntu -c "cd /srv/racedb && git reset --hard && git clean -fd && git pull"; then
    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to update helm chart repo before deployment\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    exit 1
  fi

  echo "INFO: Deploying new tag: $LATEST_TAG to RRW"
  if helm upgrade --install racedb . \
    --values values-rrw.yaml \
    --set image.tag="${LATEST_TAG}" \
    --wait --timeout 5m; then

    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"✅ Successfully upgraded *RRW* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    echo "INFO: Successfully upgraded RRW to ${LATEST_TAG}"

  else
    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to upgrade *RRW* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    echo "ERROR: Failed to upgrade RRW to ${LATEST_TAG}"
    exit 1
  fi

  echo "INFO: Deploying new tag: $LATEST_TAG to racedbdev"
  if ! helm upgrade --install racedbdev . \
    --values values-racedb.yaml \
    --set image.tag="${LATEST_TAG}" \
    --wait --timeout 5m; then

    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to upgrade *racedbdev* to *${LATEST_TAG}*\"}" \
      "$SLACK_GITLAB_WEBHOOK"
    echo "ERROR: Failed to upgrade racedbdev to ${LATEST_TAG}"
    exit 1
  fi

  echo "INFO: Deploying alloy"
  cd ../alloy
  if ! ./deploy.sh ; then

    curl -sS -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"❌ Failed to deploy *Alloy*" \
      "$SLACK_GITLAB_WEBHOOK"
    exit 1
    echo "ERROR: Failed to deploy Alloy"
  fi

else
  echo "INFO: RRW already running the latest tag: $CURRENT_TAG"

  echo "INFO: Checking for a [push dev] commit for racedb"

  CURRENT_TAG=$(kubectl get deployment racedbdev-web -o jsonpath="{.spec.template.spec.containers[*].image}" | awk -F":" '{print $2}')
  echo "INFO: Current tag: $CURRENT_TAG"

  if [ "$latest_pipeline_status" = "success" ]; then
    if [ "$CURRENT_TAG" = "$latest_pipeline_sha" ]; then
      echo "INFO: Current deployed tag ($CURRENT_TAG) is the same as latest pipeline SHA. Skipping deployment."
      exit 0
    fi

    commit_message=$(curl -s --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" \
      "https://gitlab.com/api/v4/projects/${PROJECT_ID}/repository/commits/$latest_pipeline_sha" | jq -r '.message')

    if echo "$commit_message" | grep -q '\[push dev\]'; then
      echo "INFO: Latest commit contains [push dev], updating racedbdev"

      echo "INFO: Deploying new tag: $latest_pipeline_sha to racedbdev"
      if ! helm upgrade --install racedbdev . \
        --values values-racedb.yaml \
        --set image.tag="${latest_pipeline_sha}" \
        --wait --timeout 5m; then

        curl -sS -X POST -H 'Content-type: application/json' \
          --data "{\"text\":\"❌ Failed to upgrade *racedbdev* to *${latest_pipeline_sha}*\"}" \
          "$SLACK_GITLAB_WEBHOOK"
        echo "ERROR: Failed to upgrade racedbdev to ${latest_pipeline_sha}"
        exit 1
      fi
    else
      echo "INFO: Latest commit message does NOT contain [push dev]"
    fi
  else
    echo "INFO: Latest pipeline did not succeed (status: $latest_pipeline_status), SHA: $latest_pipeline_sha"
  fi

fi
