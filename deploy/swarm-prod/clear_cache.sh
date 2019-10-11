#!/bin/bash
docker exec -it `docker ps | grep racedb_gunicorn | awk '{print $1}'` ./manage.py clear_cache
