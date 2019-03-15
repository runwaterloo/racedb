from celery import shared_task
import requests
import os
from . import secrets
from .models import Config


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")


@shared_task
def webhook():
    print("Starting git pull...")
    os.system("git pull https://gitlab.com/sl70176/racedb.git")    
    print("Starting pip install...")
    os.system("pip install -r requirements.txt")
    print("Touching wsgi.py")
    os.system("touch racedb/wsgi.py")    


@shared_task
def photoupdate():
    prod_ipaddr = secrets.prod_ipaddr
    my_ip = None
    try:
        my_ip = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4", timeout=5).text.strip()
    except Exception:
        pass
    if my_ip == prod_ipaddr:
        baseurl = "https://results.runwaterloo.com/photoupdate/"
        notifykey = Config.objects.get(name="notifykey").value    
        url = "{}/?notifykey={}&date=auto".format(baseurl, notifykey)
        r = requests.get(url)
    else:
        print("Not production host, skipping photoupdate")
