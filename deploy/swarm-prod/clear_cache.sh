#!/bin/bash
docker exec `docker ps | grep racedb_gunicorn | awk '{print $1}'` ./manage.py clear_cache
