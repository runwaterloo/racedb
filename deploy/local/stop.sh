#!/usr/bin/env bash
# Usage: ./stop.sh
set -e

echo "Stopping all containers for racedb..."
docker-compose -f deploy/local/docker-compose.yml stop

echo "All containers stopped."
