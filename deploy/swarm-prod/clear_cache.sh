#!/bin/bash
sleep 10
docker exec `docker ps | grep racedb_gunicorn | awk '{print $1}'` /usr/local/bin/python /srv/racedb/manage.py clear_cache
exit 0
