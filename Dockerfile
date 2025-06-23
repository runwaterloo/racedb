FROM python:3.13.2-alpine3.21
ARG INSTALL_TEST=0
ARG INSTALL_DEV=0
ENV PYTHONUNBUFFERED 1
COPY requirements/*.txt ./
RUN apk add --no-cache --virtual .build-deps \
     gcc \
     mariadb-dev \
     musl-dev && \
    apk add --no-cache \
     curl \
     mariadb-client \
     mariadb-connector-c-dev && \
    if [ "$INSTALL_DEV" = "1" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    elif [ "$INSTALL_TEST" = "1" ]; then \
        pip install --no-cache-dir -r requirements-test.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi && \
    apk del .build-deps
COPY . /srv/racedb
WORKDIR /srv/racedb
ENV DJANGO_SETTINGS_MODULE=racedb.settings.settings
RUN python manage.py collectstatic --noinput
