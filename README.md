# Deploying racedb

_Note: This is a work in progress, we need to iron out the bugs_

mkdir /srv
mkdir /srv/racedb_nginx
mkdir /srv/racedb_static
cd /srv
git clone git@gitlab.com:sl70176/racedb.git
cd racedb
create racedb/secrets.py
create /srv/racedb_nginx/app.conf
docker swarm init
docker build --name racedb_gunicorn -f Dockerfile-gunicorn .
docker stack deploy -c ./racedb-stack-dev-min.yml
