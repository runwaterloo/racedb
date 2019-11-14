import os
from celery import Celery

app = Celery('racedb')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.timezone = 'America/Montreal'
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

