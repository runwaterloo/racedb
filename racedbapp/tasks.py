from django.core.mail import send_mail
from django_slack import slack_message
from celery import shared_task
import requests
import os
from datetime import date
from . import process_photoupdate, secrets, view_member
from .models import Config, Rwmember
import logging

logger = logging.getLogger(__name__)


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")


@shared_task
def webhook():
    logger.info("Starting git pull...")
    os.system("git pull https://gitlab.com/sl70176/racedb.git")
    logging.info("Updating pip requirements")
    os.system("pip install -r requirements.txt")
    logging.info("Touching .restart")
    os.system("touch .restart")


@shared_task
def photoupdate(request_date=None, force=False):
    prod_ipaddr = secrets.prod_ipaddr
    my_ip = None
    try:
        my_ip = requests.get(
            "http://169.254.169.254/latest/meta-data/public-ipv4", timeout=5
        ).text.strip()
    except Exception:
        pass
    if my_ip == prod_ipaddr or force:
        process_photoupdate.index(request_date)
    else:
        logger.info("Not production host, skipping photoupdate")


@shared_task
def update_featured_member_id():
    """ Update featured_member_id to someone new """
    db_member = Config.objects.filter(name="featured_member_id")
    if db_member.count() == 0:
        Config(name="featured_member_id", value=0).save()
    current_featured_member = Config.objects.filter(name="featured_member_id")[:1][0]
    current_featured_member_id = 0
    if current_featured_member.value.isdigit():
        current_featured_member_id = int(current_featured_member.value)
    members = (
        Rwmember.objects.filter(active=True)
        .exclude(photourl=None)
        .exclude(photourl="")
        .order_by("?")
    )
    for member in members:
        member_results, km = view_member.get_memberresults(member)
        if km > 0 and member.id != current_featured_member_id:
            break
    current_featured_member.value = member.id
    current_featured_member.save()
    logger.info(
        "Changed featured member from {} to {}".format(
            current_featured_member_id, member.id
        )
    )


@shared_task
def slack_featured_member():
    prod_ipaddr = secrets.prod_ipaddr
    my_ip = None
    try:
        my_ip = requests.get(
            "http://169.254.169.254/latest/meta-data/public-ipv4", timeout=5
        ).text.strip()
    except Exception:
        pass
    if my_ip == prod_ipaddr:
        featured_member_id = int(Config.objects.get(name="featured_member_id").value)
        featured_member = Rwmember.objects.get(id=featured_member_id)
        logger.info(
            "Sending featured member ({}) to Slack".format(featured_member.name)
        )
        slack_message(
            "racedbapp/featured_member.slack", {"featured_member": featured_member}
        )
    else:
        logger.info("Not production host, skipping slack_featured_member")
