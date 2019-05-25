from django.shortcuts import render
from django.http import HttpResponse
from django.core.cache import cache

# from django.db.models import Min, Q
# from django import db
from collections import namedtuple
import urllib
import simplejson
from . import config, view_boost, view_recap, view_member, view_shared
from datetime import datetime, timedelta
from operator import attrgetter
from .models import Config, Endurraceresult, Event, Relay, Result, Rwmember

named_future_event = namedtuple("nfe", ["event", "race", "distance", "records"])

named_event = namedtuple("ne", ["date", "city"])
named_race = namedtuple("nr", ["name", "shortname", "slug"])
named_distance = namedtuple("nd", ["name", "slug", "km"])


def index(request):
    cache_key = "index.{}".format(request.META["QUERY_STRING"])
    cached_html = cache.get(cache_key)
    if cached_html:
        return cached_html  # return the page immediately if it's cached
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    asofdate = None
    if "asofdate" in qstring:
        asofdate = qstring["asofdate"][0]
    last_race_day_events = get_last_race_day_events(asofdate)
    recap_type = get_recap_type(last_race_day_events)
    distances = get_distances(last_race_day_events)
    recap_event = get_recap_event(last_race_day_events, recap_type, distances)
    recap_results = get_recap_results(recap_event, recap_type)
    memberinfo = get_memberinfo()
    featured_event = get_featured_event()
    featured_event_data = get_featured_event_data(featured_event)
    future_events = get_future_events(featured_event)
    boost_year = view_boost.get_boost_years()[0]
    boost_leaderboard = view_boost.index(request, boost_year, leaderboard_only=True)
    notification = get_notification()
    context = {
        "distances": distances,
        "recap_type": recap_type,
        "recap_event": recap_event,
        "recap_results": recap_results,
        "memberinfo": memberinfo,
        "featured_event": featured_event,
        "featured_event_data": featured_event_data,
        "future_events": future_events,
        "boost_year": boost_year,
        "boost_leaderboard": boost_leaderboard,
        "notification": notification,
    }
    # Determine the format to return based on what is seen in the URL
    if "format" in qstring:
        if qstring["format"][0] == "json":
            data = simplejson.dumps(context, default=str, indent=4, sort_keys=True)
            if "callback" in qstring:
                callback = qstring["callback"][0]
                data = "{}({});".format(callback, data)
                return HttpResponse(data, "text/javascript")
            else:
                return HttpResponse(data, "application/json")
        else:
            return HttpResponse("Unknown format in URL", "text/html")
    else:
        html = render(request, "racedbapp/index.html", context)
        cache.set(cache_key, html)
        return html


def get_future_events(featured_event):
    today = datetime.today()
    future_events = []
    dbfuture_events = Event.objects.filter(date__gte=today).order_by(
        "date", "-distance__km"
    )
    upcoming_races_count = int(
        Config.objects.get(name="homepage_upcoming_races_count").value
    )
    races_seen = []
    for i in dbfuture_events:
        if len(races_seen) == upcoming_races_count:
            if i.race not in races_seen:
                break
        if i == featured_event:
            continue
        event_result_count = Result.objects.filter(event=i).count()
        if event_result_count > 0:
            continue
        event = named_event(i.date, i.city)
        race = named_race(i.race.name, i.race.shortname, i.race.slug)
        distance = named_distance(i.distance.name, i.distance.slug, i.distance.km)
        numresults = Result.objects.filter(
            event__race=i.race, event__distance=i.distance
        ).count()
        records = False
        if numresults > 0:
            records = view_shared.getracerecords(
                i.race, i.distance, individual_only=True
            )
        future_events.append(named_future_event(event, race, distance, records))
        if i.race not in races_seen:
            races_seen.append(i.race)
    return future_events


def get_memberinfo():
    named_memberinfo = namedtuple(
        "nm", ["member", "racing_since", "km", "fivek_pb", "tenk_pb"]
    )
    members = (
        Rwmember.objects.filter(active=True)
        .exclude(photourl=None)
        .exclude(photourl="")
        .order_by("?")
    )
    featured_member_id = "0"
    db_featured_member_id = Config.objects.filter(name="featured_member_id")
    if db_featured_member_id.count() > 0:
        featured_member_id = db_featured_member_id[0].value
    if featured_member_id.isdigit():
        featured_member_id = int(featured_member_id)
    valid_member_ids = [x.id for x in members]
    if featured_member_id in valid_member_ids:
        member = [x for x in members if x.id == featured_member_id][0]
        member_results, km = view_member.get_memberresults(member)
    else:
        for member in members:
            member_results, km = view_member.get_memberresults(member)
            if km > 0:
                break
    km = round(km, 1)
    racing_since = ""
    fivek_pb = view_member.get_pb(member_results, "5-km")
    tenk_pb = view_member.get_pb(member_results, "10-km")
    if len(member_results) > 0:
        racing_since = member_results[-1].result.event.date.year
    memberinfo = named_memberinfo(member, racing_since, km, fivek_pb, tenk_pb)
    return memberinfo


def get_featured_event():
    featured_event = None
    try:
        featured_event_id = int(
            Config.objects.get(name="homepage_featured_event_id").value
        )
    except Exception:
        pass
    else:
        try:
            event = Event.objects.get(id=featured_event_id)
        except Exception:
            pass
        else:
            finishers = Result.objects.filter(event=event).count()
            if finishers == 0:
                featured_event = event
    return featured_event


def get_featured_event_data(featured_event):
    featured_event_data = get_event_data(featured_event)
    return featured_event_data


def get_event_data(featured_event):
    if not featured_event:
        return None
    previous_event_year = featured_event.date.year - 1
    previous_event = Event.objects.get(
        race=featured_event.race,
        distance=featured_event.distance,
        date__icontains=previous_event_year,
    )
    previous_event_recap = get_recap_results_standard(previous_event)
    featured_event_records = view_shared.getracerecords(
        featured_event.race, featured_event.distance, individual_only=True
    )
    featured_event_data = []
    for i in featured_event_records:
        row = UpcomingEvent()
        row.demographic = i.place
        row.record_athlete = i.athlete
        row.record_member = i.member
        row.record_time = i.guntime
        row.record_year = i.year
        recap_row = 0
        if "Master" in row.demographic:
            recap_row = 1
        if "Female" in row.demographic:
            row.last_year_winning_athlete = previous_event_recap[
                recap_row
            ].female_athlete
            row.last_year_winning_member = previous_event_recap[
                recap_row
            ].female_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].female_time
        else:
            row.last_year_winning_athlete = previous_event_recap[recap_row].male_athlete
            row.last_year_winning_member_slug = previous_event_recap[
                recap_row
            ].male_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].male_time
        featured_event_data.append(row)
    return featured_event_data


def get_recap_event(last_race_day_events, recap_type, distances):
    """ Choose which event to use for a recap """
    distance_slugs = [x.slug for x in distances]
    if recap_type == "relay" and "2_5-km" in distance_slugs:
        recap_event = last_race_day_events.filter(distance__slug="2_5-km")[0]
    else:
        recap_event = last_race_day_events[0]
    return recap_event


def get_recap_results(recap_event, recap_type):
    if recap_type == "relay":
        recap_results = get_recap_results_relay(recap_event)
    elif recap_type == "combined":
        recap_results = get_recap_results_combined(recap_event)
    else:
        recap_results = get_recap_results_standard(recap_event)
    return recap_results


def get_recap_results_standard(recap_event):
    event_results = Result.objects.filter(event=recap_event)
    hasmasters = Result.objects.hasmasters(recap_event)
    distance_slug = recap_event.distance.slug
    recap_results = view_recap.get_individual_results(
        recap_event, event_results, hasmasters, distance_slug
    )
    return recap_results


def get_recap_results_relay(recap_event):
    relay_records = view_shared.get_relay_records(year=recap_event.date.year)
    categories = config.ValidRelayCategories().categories.values()
    recap_results = {}
    for i in categories:
        if relay_records[i]:
            fastest_times = relay_records[i]
            winner = sorted(fastest_times, key=attrgetter("team_place"))[0]
            recap_results[i] = winner
    return recap_results


def get_recap_results_combined(recap_event):
    request = {}
    year = recap_event.date.year
    race_slug = recap_event.race.slug
    distance_slug = "combined"
    recap_results = view_recap.index(
        request, year, race_slug, distance_slug, individual_only=True
    )
    return recap_results


def get_distances(last_race_day_events):
    distances = [x.distance for x in last_race_day_events]
    return distances


def get_last_race_day_events(asofdate):
    if asofdate:
        maxdate = datetime.strptime(asofdate, "%Y-%m-%d")
        date_of_last_event = (
            Result.objects.all()
            .filter(event__date__lte=maxdate)
            .order_by("-event__date")[:1][0]
            .event.date
        )
    else:
        date_of_last_event = (
            Result.objects.all().order_by("-event__date")[:1][0].event.date
        )
    last_race_day_event_ids = (
        Result.objects.filter(event__date=date_of_last_event)
        .values_list("event", flat=True)
        .distinct()
    )
    last_race_day_events = Event.objects.filter(
        id__in=last_race_day_event_ids
    ).order_by("-distance__km")
    return last_race_day_events


def get_recap_type(last_race_day_events):
    recap_type = "standard"
    if last_race_day_events[0].race.slug == "laurier-loop":
        relay_event = [x for x in last_race_day_events if x.distance.slug == "2_5-km"]
        if len(relay_event) == 1:
            if Relay.objects.filter(event=relay_event[0]).count() > 0:
                recap_type = "relay"
    if last_race_day_events[0].race.slug == "endurrace":
        year = last_race_day_events[0].date.year
        if Endurraceresult.objects.filter(year=year).count() > 0:
            recap_type = "combined"
    return recap_type


def get_notification():
    notification = False
    notifications = Config.objects.filter(name="homepage_notification")
    if len(notifications) == 1:
        dbvalue = notifications[0].value
        if dbvalue != "":
            notification = dbvalue
    return notification


class UpcomingEvent:
    def __init__(self):
        self.demographic = None
        self.last_year_winning_athlete = None
        self.last_year_winning_member_slug = None
        self.last_year_winning_time = None
        self.record_athlete = None
        self.record_time = None
        self.record_year = None
