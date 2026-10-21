import logging
import os
import urllib
from datetime import date, timedelta

import requests
from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connection
from django.test import Client
from django.utils import timezone
from django_slack import slack_message

from . import process_photoupdate, view_member
from .models import Config, Endurathlete, Event, Rwmember, Rwmembertag
from .shared import cache_lock
from .shared.shared import get_config_value_or_false

logger = logging.getLogger(__name__)

WARM_URLS = ["/"]

WEBHOST = os.getenv("WEBHOST", "http://localhost")


def safe_enqueue(task, *args, **kwargs):
    """Enqueue a Celery task, tolerating an unreachable broker.

    Local dev often runs without a broker (SETTINGS=min has no
    CELERY_BROKER_URL, so Celery would default to RabbitMQ on localhost
    if a task were enqueued; production broker is Redis).
    Queueing failures should degrade to a log line, not break the
    request or import that triggered them.
    """
    task_name = getattr(task, "name", str(task))
    try:
        result = task.delay(*args, **kwargs)
        logger.info("Enqueued task {}".format(task_name))
        return result
    except Exception:
        logger.warning(
            "Could not enqueue task {} (broker unavailable?) - continuing".format(task_name)
        )
        return None


@shared_task
def heartbeat():
    os.system("touch /srv/racedb/.heartbeat")


@shared_task
def webhook():
    logger.info("Starting git pull...")
    os.system("git pull https://gitlab.com/sl70176/racedb.git")
    logging.info("Updating pip requirements")
    os.system("pip install -r requirements.txt")
    # clear_cache bumps the generation and warms hot pages; the warm task
    # survives the .restart (queued in the Redis broker, redelivered after
    # startup) so post-deploy visitors hit warm cache, not cold renders.
    safe_enqueue(clear_cache)
    logging.info("Touching .restart")
    os.system("touch .restart")


CACHE_WATCHER_STATE_KEY = "cache_watcher.fingerprint"
CACHE_WATCHER_LAST_RUN_KEY = "cache_watcher.last_run"


@shared_task
def db_cache_watcher():
    """Bump the cache generation when the DB changes (fixes #387).

    Every minute, compare a pg_stat fingerprint of racedbapp_* table change
    counters against the previous run. A difference means the DB changed,
    which the signals-based invalidation cannot always see (e.g. photoupdate
    adding photo tags), so bump the cache generation.

    Config knobs:
    - cache_watcher_dry_run (default true): log what would happen, don't bump
    - cache_watcher_debug: log the fingerprint comparison when nothing changed
    - cache_watcher_interval_seconds (default 60): check frequency; beat
      fires every minute and the task no-ops when not yet due
    """
    now = timezone.now().timestamp()
    last_run = cache.get(CACHE_WATCHER_LAST_RUN_KEY)
    if last_run is not None:
        interval = _watcher_config_float("cache_watcher_interval_seconds", 60.0)
        if now - last_run < interval:
            return
    cache.set(CACHE_WATCHER_LAST_RUN_KEY, now, None)
    current = _get_fingerprint()
    if current is None:
        return
    previous = cache.get(CACHE_WATCHER_STATE_KEY)
    cache.set(CACHE_WATCHER_STATE_KEY, current, None)
    if previous is None:
        logger.info("cache watcher: first run, storing fingerprint (no bump)")
        return
    if current == previous:
        if _watcher_config_bool("cache_watcher_debug", False):
            logger.debug("cache watcher: no DB changes, fingerprint unchanged")
        return
    deltas = _fingerprint_deltas(previous, current)
    if _watcher_config_bool("cache_watcher_dry_run", True):
        logger.info("cache watcher: DRY RUN, would bump cache generation: %s", deltas)
    else:
        logger.info("cache watcher: DB changed, bumping cache generation: %s", deltas)
        cache_lock.bump_generation()


def _get_fingerprint():
    """Return {table: (ins, upd, del)} from pg_stat_user_tables, or None.

    None means "cannot fingerprint" (non-postgres, e.g. sqlite in tests):
    the watcher then does nothing, so local dev and tests are unaffected.
    """
    if connection.vendor != "postgresql":
        return None
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relname, n_tup_ins, n_tup_upd, n_tup_del "
                "FROM pg_stat_user_tables WHERE relname LIKE 'racedbapp_%'"
            )
            rows = cursor.fetchall()
    except Exception:
        logger.exception("cache watcher: fingerprint query failed")
        return None
    return {row[0]: (row[1], row[2], row[3]) for row in rows}


def _fingerprint_deltas(previous, current):
    deltas = {}
    for table, counters in current.items():
        prev = previous.get(table)
        if prev is None:
            deltas[table] = "new table, counters {}".format(counters)
            continue
        delta = tuple(c - p for c, p in zip(counters, prev))
        if any(delta):
            deltas[table] = delta
    for table in previous:
        if table not in current:
            deltas[table] = "table gone"
    return deltas


def _watcher_config_bool(name, default):
    value = get_config_value_or_false(name)
    if value is False:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _watcher_config_float(name, default):
    value = get_config_value_or_false(name)
    if value is False:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("cache watcher: invalid %s=%r, using %s", name, value, default)
        return default

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
    """Invalidate all generation-stamped cache entries, then warm hot pages.

    Kept for the notifykey endpoint and addraces; does a generation bump,
    not a cache.clear().
    """
    logger.info("Bumping cache generation")
    cache_lock.bump_generation()
    safe_enqueue(warm_cache)


@shared_task
def warm_cache():
    """Render hot pages so the next visitors get cache hits, not cold renders."""
    if WEBHOST == "http://localhost":
        client = Client()
        for url in WARM_URLS:
            logger.info("Warming cache: %s", url)
            response = client.get(url)
            logger.info("Warmed %s -> %s", url, response.status_code)
    else:
        for url in WARM_URLS:
            host = WEBHOST
            if not host.startswith(("http://", "https://")):
                host = "https://" + host
            full_url = urllib.parse.urljoin(host, url)
            logger.info("Warming cache: %s", full_url)
            try:
                response = requests.get(full_url, timeout=30)
                logger.info("Warmed %s -> %s", full_url, response.status_code)
            except requests.RequestException as e:
                logger.warning("Failed to warm %s: %s", full_url, e)


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
