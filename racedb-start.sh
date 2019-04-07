#!/bin/bash
./manage.py collectstatic --noinput
gunicorn racedb.wsgi -b 0.0.0.0:8000
