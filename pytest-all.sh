docker exec racedb-web sh -c \
 'DJANGO_SETTINGS_MODULE=racedb.settings.min \
  DISABLE_DEBUG_TOOLBAR=true \
  pytest -v -m "integration or not integration"'
