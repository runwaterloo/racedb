FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN apt-get update
RUN apt-get install -y mariadb-client
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkdir /srv/racedb
COPY . /srv/racedb
WORKDIR /srv/racedb
