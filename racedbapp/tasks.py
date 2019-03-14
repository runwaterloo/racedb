from celery import shared_task
import os


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")



