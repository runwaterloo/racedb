#!/bin/bash
docker build -t racedb .
IMAGE_ID=`docker image ls | grep racedb | grep latest | awk '{print $3}'`
docker tag racedb:latest racedb:$IMAGE_ID
echo $IMAGE_ID
cp -f deploy/swarm-dev/docker-compose-dev.yml /srv
sed -i s/racedb:latest/racedb:$IMAGE_ID/g /srv/docker-compose-dev.yml
env BUILD=$IMAGE_ID docker stack deploy -c /srv/docker-compose-dev.yml racedb
docker system prune -f
sleep 8
docker exec -it `docker ps | grep racedb_gunicorn | awk '{print $1}'` ./manage.py clear_cache
