#!/bin/bash
docker exec -i `docker ps | grep racedb_gunicorn | head -n 1 | awk '{print $1}'` /usr/local/bin/python /srv/racedb/manage.py clear_cache --settings=racedb.settings.prod