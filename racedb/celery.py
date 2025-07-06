from celery import Celery

app = Celery("racedb")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.timezone = "America/Montreal"
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print("Request: {!r}".format(self.request))
