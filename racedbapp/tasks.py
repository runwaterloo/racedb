from celery import shared_task
import requests
import os
from . import secrets
from . import process_photoupdate
import logging                                                                           
                                                                                         
logger = logging.getLogger(__name__)  


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")


@shared_task
def webhook():
    logger.info("Starting git pull...")
    os.system("git pull https://gitlab.com/sl70176/racedb.git")    
    logger.info("Starting pip install...")
    os.system("pip install -r requirements.txt")
    logger.info("Touching wsgi.py")
    os.system("touch racedb/wsgi.py")    


@shared_task
def photoupdate(request_date=None, force=False):
    prod_ipaddr = secrets.prod_ipaddr
    my_ip = None
    try:
        my_ip = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4", timeout=5).text.strip()
    except Exception:
        pass
    if my_ip == prod_ipaddr or force:
        process_photoupdate.index(request_date)
    else:
        logger.info("Not production host, skipping photoupdate")
