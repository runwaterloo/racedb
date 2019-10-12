#!/bin/bash
sleep 10
docker ps | grep racedb_gunicorn
docker exec -i `docker ps | grep racedb_gunicorn | awk '{print $1}'` /usr/local/bin/python /srv/racedb/manage.py clear_cache
exit 0
