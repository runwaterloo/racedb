#!/bin/bash
docker build -t racedb .
IMAGE_ID=`docker image ls | grep racedb | grep latest | awk '{print $3}'`
docker tag racedb:latest racedb:$IMAGE_ID
echo $IMAGE_ID
cp -f deploy/swarm-dev/racedb-stack-dev.yml /srv
sed -i s/racedb:latest/racedb:$IMAGE_ID/g /srv/racedb-stack-dev.yml
env BUILD=$IMAGE_ID docker stack deploy -c /srv/racedb-stack-dev.yml racedb
docker system prune -f
