#!/bin/bash
sleep 10
docker exec -i `docker ps | grep racedb_gunicorn | head -n 1 | awk '{print $1}'` /usr/local/bin/python /srv/racedb/manage.py clear_cache
exit 0
