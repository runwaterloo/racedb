#!/bin/bash
mkdir -p /srv/racedb_secrets_dev
aws s3 cp --recursive s3://${BUCKET}/racedb_secrets_dev/ /srv/racedb_secrets_dev/
