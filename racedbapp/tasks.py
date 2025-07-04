import logging
import os
from datetime import date, timedelta

from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail
from django_slack import slack_message

from racedb import secrets

from . import process_photoupdate, view_member
from .models import Config, Endurathlete, Event, Rwmember, Rwmembertag

logger = logging.getLogger(__name__)

WEBHOST = os.getenv("WEBHOST", "http://localhost")


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")


@shared_task
def webhook():
    logger.info("Starting git pull...")
    os.system("git pull https://gitlab.com/sl70176/racedb.git")
    logging.info("Updating pip requirements")
    os.system("pip install -r requirements.txt")
    logging.info("Clearing cache")
    cache.clear()
    logging.info("Touching .restart")
    os.system("touch .restart")


@shared_task
def photoupdate(request_date=None, force=False):
    if WEBHOST == "results.runwaterloo.com":
        process_photoupdate.index(request_date)
    else:
        logger.info("Not production host, skipping photoupdate")


@shared_task
def update_featured_member_id():
    """Update featured_member_id to someone new"""
    db_member = Config.objects.filter(name="featured_member_id")
    if db_member.count() == 0:
        Config(name="featured_member_id", value=0).save()
    featured_member_no_repeat_days = int(
        Config.objects.get(name="featured_member_no_repeat_days").value
    )
    db_featured_member_history = Config.objects.get(name="featured_member_history")
    featured_member_history = db_featured_member_history.value
    str_featured_member_history = featured_member_history.split(",")
    featured_member_history = [int(x) for x in str_featured_member_history]
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
    featured_member_tag_config = Config.objects.filter(name="featured_member_tag").first()
    if featured_member_tag_config is not None:
        featured_member_tag = Rwmembertag.objects.filter(
            name=featured_member_tag_config.value
        ).first()
        if featured_member_tag is not None:
            members = members.filter(tags=featured_member_tag)
    member = False
    featured_member_id_next = Config.objects.filter(name="featured_member_id_next").first()
    if featured_member_id_next is not None:
        if featured_member_id_next.value.isdigit():
            if int(featured_member_id_next.value) in [x.id for x in members]:
                member = Rwmember.objects.get(id=featured_member_id_next.value)
                featured_member_id_next.value = ""
                featured_member_id_next.save()
    if not member:
        db_ultimates = False
        if date.today().month == 8:
            db_ultimates = Endurathlete.objects.filter(
                year=date.today().year, division="Ultimate"
            ).values_list("name", flat=True)
        if len(members) > featured_member_no_repeat_days:
            members = members.exclude(id__in=featured_member_history)
        for member in members:
            member_results, km = view_member.get_memberresults(member)
            if km > 0:
                if db_ultimates:
                    if member.name in db_ultimates:
                        break
                    else:
                        continue
                else:
                    break
    current_featured_member.value = member.id
    current_featured_member.save()
    featured_member_history.append(member.id)
    trim_featured_member_history = featured_member_history[-featured_member_no_repeat_days:]
    str_featured_member_history = ",".join(str(v) for v in trim_featured_member_history)
    db_featured_member_history.value = str_featured_member_history
    db_featured_member_history.save()
    logger.info(
        "Changed featured member from {} to {}".format(current_featured_member_id, member.id)
    )


@shared_task
def slack_featured_member():
    if WEBHOST == "results.runwaterloo.com":
        featured_member_id = int(Config.objects.get(name="featured_member_id").value)
        featured_member = Rwmember.objects.get(id=featured_member_id)
        logger.info("Sending featured member ({}) to Slack".format(featured_member.name))
        slack_message("racedbapp/featured_member.slack", {"featured_member": featured_member})
    else:
        logger.info("Not production host, skipping slack_featured_member")


@shared_task
def slack_results_update(results):
    if WEBHOST == "results.runwaterloo.com":
        logger.info("Sending results update to Slack")
        slack_message("racedbapp/results_update.slack", {"results": results})
    else:
        logger.info("Not production host, skipping slack_results_update")


@shared_task
def slack_missing_urls():
    if WEBHOST == "results.runwaterloo.com":
        logger.info("Checking for events with no URL")
        missing_urls = []
        days = int(Config.objects.get(name="missing_url_alert_days").value)
        today = date.today()
        endday = today + timedelta(days=days)
        upcoming_events = (
            Event.objects.filter(date__gt=today).filter(date__lte=endday).order_by("date")
        )
        for event in upcoming_events:
            if "http" not in event.resultsurl:
                missing_urls.append(event)
        if len(missing_urls) > 0:
            logger.info("Sending missing URLs to Slack")
            slack_message(
                "racedbapp/missing_urls.slack",
                {"days": days, "missing_urls": missing_urls},
            )
    else:
        logger.info("Not production host, skipping missing_urls")


@shared_task
def clear_cache():
    logger.info("Clearing cache")
    cache.clear()


@shared_task
def send_email_task(subject, content, recipients):
    from_addr = Config.objects.get(name="email_from_address").value
    logger.info("Attempting to send email")
    send_mail(
        subject,
        content,
        from_addr,
        recipients,  # should be a list
        fail_silently=False,
    )
    logger.info("Email sent!")


@shared_task
def dump_database():
    if WEBHOST == "results.runwaterloo.com":
        logger.info("Dumping database to /tmp/racedb.sql.gz")
        os.system(
            "mysqldump -h {} -u racedb --password={} --skip-dump-date racedb > /tmp/racedb.sql".format(
                secrets.DB_HOST, secrets.DB_PASSWORD
            )
        )
        os.system("gzip -f /tmp/racedb.sql")
    else:
        logger.info("Not production host, skipping database dump")
