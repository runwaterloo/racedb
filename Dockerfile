FROM python:3.7.4-alpine
ENV PYTHONUNBUFFERED 1
RUN apk add --no-cache --virtual \
    ca-certificates \
    curl \
    gcc \
    mariadb-client \
    mariadb-connector-c-dev \
    musl-dev \
    zlib-dev
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /srv/racedb
WORKDIR /srv/racedb
