#!/bin/bash
# Seeding: no traces (build/data-load noise, not runtime signal)
docker exec -e TRACING=off racedb-web sh -c 'find racedbapp/fixtures -name "*.yaml" | xargs python ./manage.py loaddata'
docker exec -e TRACING=off racedb-web sh -c 'python ./manage.py generate_fake_rwmembers'
docker exec -e TRACING=off racedb-web sh -c 'python ./manage.py generate_fake_boost'
docker exec -e TRACING=off racedb-web sh -c 'python ./manage.py generate_fake_results'
