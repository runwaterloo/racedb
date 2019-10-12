#!/bin/bash
docker exec --rm -i `docker ps | grep racedb_gunicorn | awk '{print $1}'` ./manage.py clear_cache
exit 0
