#/bin/bash
docker exec `docker container ls | grep racedb_django | awk '{print $1}'` ./manage.py collectstatic --no-input --settings=racedb.settings.min
docker exec `docker container ls | grep racedb_django | awk '{print $1}'` ./manage.py test --settings=racedb.settings.min