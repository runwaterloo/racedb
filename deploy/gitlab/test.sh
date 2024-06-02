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

# Execute the test command inside the Docker container
docker exec racedb_gunicorn ./manage.py test --settings=racedb.settings.min
