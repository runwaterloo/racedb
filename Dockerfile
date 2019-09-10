FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install -y mariadb-client
RUN mkdir /config
ADD requirements.txt /config/
RUN pip install -r /config/requirements.txt
RUN mkdir /srv/racedb
WORKDIR /srv/racedb
