FROM python:3.14.3-alpine
ARG INSTALL_TEST=0
ARG INSTALL_DEV=0
ENV PYTHONUNBUFFERED=1
COPY requirements/*.txt ./
RUN \
    if [ "$INSTALL_DEV" = "1" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    elif [ "$INSTALL_TEST" = "1" ]; then \
        pip install --no-cache-dir -r requirements-test.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi
COPY . /srv/racedb
WORKDIR /srv/racedb
ENV DJANGO_SETTINGS_MODULE=racedb.settings.settings
ENV SETTINGS=prod
COPY racedb/secrets.py.sample racedb/secrets.py
RUN python manage.py collectstatic --noinput && rm racedb/secrets.py
