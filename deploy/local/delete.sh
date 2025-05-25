#!/usr/bin/env bash
# Usage: ./delete.sh
set -e

echo "Stopping and removing all containers, networks, and volumes for racedb..."
docker-compose -f deploy/local/docker-compose.yml down -v

echo "All containers, networks, and volumes removed."
