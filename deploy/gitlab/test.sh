#!/bin/bash

# Check if CI_COMMIT_BRANCH equals CI_DEFAULT_BRANCH
if [ "$CI_COMMIT_BRANCH" == "$CI_DEFAULT_BRANCH" ]; then
  echo "Skipping test.sh in $CI_COMMIT_BRANCH branch"
  exit 0
fi

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

# Execute unit and integration tests inside the Docker container
docker exec racedb-web sh -c '
  export DJANGO_SETTINGS_MODULE=racedb.settings.min &&
  export DISABLE_DEBUG_TOOLBAR=true &&
  pytest racedbapp/tests/test_*.py racedbapp/tests/integration_tests.py -v --junitxml=/tmp/report.xml
'
