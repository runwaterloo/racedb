#!/bin/bash
sleep 10
docker exec -i `docker ps | grep racedb_gunicorn | grep starting | awk '{print $1}'` /usr/local/bin/python /srv/racedb/manage.py clear_cache
exit 0
