#!/bin/bash
cd /srv/racedb
docker build -t racedb:dev .
docker service update -d racedb_redis --force
docker service update -d racedb_gunicorn --force
docker service update -d racedb_celery --force
docker service update -d racedb_beat --force
docker system prune -f &
