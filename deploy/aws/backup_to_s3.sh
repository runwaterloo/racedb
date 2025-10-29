#!/bin/bash

set -euo pipefail

POD=$(kubectl get pods -l "app.kubernetes.io/instance=racedb,app.kubernetes.io/name=racedb,app.kubernetes.io/task=celery" -o jsonpath='{.items[0].metadata.name}')
LOCAL_FILE="/tmp/racedb.sql.gz"
S3_BUCKET=$(grep -E "^S3_PRIVATE_BUCKET\s*=\s*['\"]" /srv/racedb_secrets/secrets.py | sed -E "s/.*=\s*['\"]([^'\"]+)['\"].*/\1/")
S3_PREFIX="database_backup/racedb"

TZ="America/Toronto"
HOUR=$(TZ=$TZ date +%-H)
MONTHDAY=$(TZ=$TZ date +%-d)
MONTH=$(TZ=$TZ date +%-m)
WEEKDAY=$(TZ=$TZ date +%-u)
WEEK=$(TZ=$TZ date +%-V)

upload_to_s3() {
  local key=$1
  echo "Uploading ${LOCAL_FILE} to s3://${S3_BUCKET}/${key}"
  aws s3 cp "$LOCAL_FILE" "s3://${S3_BUCKET}/${key}"
}

echo "Copying /tmp/racedb.sql.gz from pod $POD to $LOCAL_FILE"
kubectl cp "$POD:/tmp/racedb.sql.gz" "$LOCAL_FILE"

if [ "$HOUR" -eq 0 ]; then
  if [ "$MONTHDAY" -eq 1 ]; then
    MONTH_MOD=$(( MONTH % 4 ))
    KEY="${S3_PREFIX}.monthly${MONTH_MOD}.sql.gz"
    upload_to_s3 "$KEY"
  elif [ "$WEEKDAY" -eq 1 ]; then
    WEEK_MOD=$(( WEEK % 4 ))
    KEY="${S3_PREFIX}.weekly${WEEK_MOD}.sql.gz"
    upload_to_s3 "$KEY"
  else
    DAY_IDX=$(( WEEKDAY - 1 ))
    KEY="${S3_PREFIX}.day${DAY_IDX}.sql.gz"
    upload_to_s3 "$KEY"
  fi
else
  KEY="${S3_PREFIX}.hour${HOUR}.sql.gz"
  upload_to_s3 "$KEY"
fi

sleep 2
KEY="${S3_PREFIX}.latest.sql.gz"
upload_to_s3 "$KEY"

echo "Backup and upload complete."
