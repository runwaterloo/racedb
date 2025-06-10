#!/usr/bin/env bash
# Usage: ./start.sh [--rebuild]
set -e

# Check if --rebuild is given or racedb-web container does not exist
if [[ "$1" == "--rebuild" ]] || ! docker ps -a --format '{{.Names}}' | grep -q '^racedb-web$'; then
  # Stop/remove if containers exist
  if docker ps -a --format '{{.Names}}' | grep -q '^racedb-web$'; then
    echo "Stopping and removing existing containers..."
    docker-compose -f deploy/local/docker-compose.yml down || true
  fi

  echo "Installing Python dev requirements..."
  pip install -r requirements/requirements-dev.txt

  echo "Starting containers in detached mode..."
  docker-compose -f deploy/local/docker-compose.yml up --build -d

  echo "Waiting for Django to be ready..."
  until
    docker exec -it racedb-web sh -c './manage.py showmigrations' | tail -n 1 | grep -q "\\[X\\]"; do
    sleep 2
  done

  echo "Django is ready. Loading fake data..."
  ./deploy/local/loaddata.sh

else
  echo "Starting containers..."
  docker-compose -f deploy/local/docker-compose.yml up -d

fi
  echo
  echo "STARTUP COMPLETE!"
  echo
  echo "You can now access the application at http://localhost:8000"
  echo
  echo "To follow logs, run:"
  echo
  echo "docker-compose -f deploy/local/docker-compose.yml logs -f"
