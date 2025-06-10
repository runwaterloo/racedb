#!/bin/bash
docker exec racedb-web sh -c 'find racedbapp/fixtures -name "*.yaml" | xargs python ./manage.py loaddata'
docker exec racedb-web sh -c 'python ./manage.py generate_fake_rwmembers'
docker exec racedb-web sh -c 'python ./manage.py generate_fake_results'
