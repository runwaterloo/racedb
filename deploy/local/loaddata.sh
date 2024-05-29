#!/bin/bash
docker exec racedb-web sh -c 'find racedbapp/fixtures -name "*.yaml" | xargs ./manage.py loaddata --settings=racedb.settings.min'
