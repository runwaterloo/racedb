FROM python:3.10.4-alpine3.16
ENV PYTHONUNBUFFERED 1
COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps \
     gcc \
     musl-dev && \
    apk add --no-cache \
     curl \
     mariadb-client \
     mariadb-connector-c-dev && \
    pip install -r requirements.txt && \
    apk del .build-deps
COPY . /srv/racedb
WORKDIR /srv/racedb
