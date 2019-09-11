FROM python:3.7.4-alpine
ENV PYTHONUNBUFFERED 1
RUN apk add --no-cache --virtual \
    ca-certificates \
    gcc \
    mariadb-client \
    mariadb-connector-c-dev \
    musl-dev \
    zlib-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkdir /srv/racedb
RUN mkdir /srv/racedb/.cache
COPY . /srv/racedb
WORKDIR /srv/racedb
