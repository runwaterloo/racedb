#!/bin/bash

# Export the MariaDB IP address
export MARIADB_IP=$(getent ahostsv4 mariadb | awk 'NR==1 { print $1 }')

# Run the deploy script
/bin/ash deploy/minimal/deploy.sh

# Collect static
docker exec racedb-web ./manage.py collectstatic --noinput --settings=racedb.settings.min;

# Create tables
docker exec racedb-web ./manage.py migrate --noinput --settings=racedb.settings.min;

# Execute all tests (unit and integration) inside the Docker container
docker exec racedb-web sh -c \
 'DJANGO_SETTINGS_MODULE=racedb.settings.min \
  DISABLE_DEBUG_TOOLBAR=true \
  pytest \
  --junitxml=/tmp/report.xml'

# Copy the test reports to the host machine
docker cp racedb-web:/tmp/report.xml report.xml
