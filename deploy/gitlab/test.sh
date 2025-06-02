#!/bin/bash

# Export the MariaDB IP address
export MARIADB_IP=$(getent ahostsv4 mariadb | awk 'NR==1 { print $1 }')

# Run the deploy script
/bin/ash deploy/minimal/deploy.sh

# Collect static
docker exec racedb-web ./manage.py collectstatic --noinput --settings=racedb.settings.min;

# Create tables
docker exec racedb-web ./manage.py migrate --noinput --settings=racedb.settings.min;

# Load data
/bin/ash deploy/local/loaddata.sh

# Execute all tests (unit and integration) inside the Docker container
docker exec racedb-web sh -c \
 'DJANGO_SETTINGS_MODULE=racedb.settings.min \
  DISABLE_DEBUG_TOOLBAR=true \
  pytest -v -m "integration or not integration" \
  --junitxml=/tmp/report.xml'

# Copy the test report to the host machine
docker cp racedb-web:/tmp/report.xml report.xml
