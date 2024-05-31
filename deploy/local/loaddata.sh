#!/bin/bash
docker exec racedb-web sh -c 'find racedbapp/fixtures -name "*.yaml" | xargs ./manage.py loaddata --settings=racedb.settings.min'
docker exec racedb-web sh -c './manage.py generate_fake_rwmembers --settings=racedb.settings.min'
docker exec racedb-web sh -c './manage.py generate_fake_results --settings=racedb.settings.min'
