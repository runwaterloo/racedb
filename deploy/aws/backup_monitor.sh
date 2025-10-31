#!/bin/bash

set -euo pipefail

# log output to systemd journal
exec > >(systemd-cat -t backup_monitor) 2>&1

if [ $# -ne 2 ]; then
  echo "Usage: $0 <bucket-name> <object-key>"
  exit 1
fi

BUCKET="$1"
KEY="$2"

HEAD_OBJECT_JSON=$(aws s3api head-object --bucket "$BUCKET" --key "$KEY")
LAST_MODIFIED=$(echo "$HEAD_OBJECT_JSON" | jq -r '.LastModified')
SIZE=$(echo "$HEAD_OBJECT_JSON" | jq -r '.ContentLength')

if [ -z "$LAST_MODIFIED" ] || [ -z "$SIZE" ]; then
  echo "Error: Could not retrieve LastModified or ContentLength for s3://$BUCKET/$KEY"
  exit 2
fi

LAST_MODIFIED_EPOCH=$(date -d "$LAST_MODIFIED" +%s)
NOW_EPOCH=$(date +%s)
AGE=$((NOW_EPOCH - LAST_MODIFIED_EPOCH))

echo "{\"task\": \"backup_monitor\", \"db\": \"postgres\", \"backup_age_seconds\": $AGE, \"backup_size_bytes\": $SIZE}"
