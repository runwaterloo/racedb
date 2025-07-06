import urllib

# from django.db.models import Min, Q
# from django import db
from collections import namedtuple
from datetime import datetime
from operator import attrgetter

import simplejson
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render

from . import config, view_endurrun, view_member, view_recap
from .models import Config, Endurraceresult, Event, Relay, Result, Rwmember
from .shared import shared, utils

EventContext = namedtuple("EventContext", ["date", "city"], defaults=(None, None))
RaceContext = namedtuple("RaceContext", ["name", "shortname", "slug"], defaults=(None, None, None))
DistanceContext = namedtuple("DistanceContext", ["name", "slug", "km"], defaults=(None, None, None))
MemberInfoContext = namedtuple(
    "MemberInfoContext",
    ["member", "racing_since", "km", "fivek_pb", "tenk_pb"],
    defaults=(None, None, None, None, None),
)
RecapContext = namedtuple(
    "RecapContext",
    ["results", "event", "type", "distances", "race_logo_slug"],
    defaults=(None, None, None, None),
)
FeaturedEventContext = namedtuple(
    "FeaturedEventContext",
    ["event", "data", "future_events", "race_logo_slug"],
    defaults=(None, None, None),
)


def index(request):
    cache_key = "index.{}".format(request.META["QUERY_STRING"])
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    asofdate = None
    if "asofdate" in qstring:
        asofdate = qstring["asofdate"][0]
    else:
        cached_html = cache.get(cache_key)
        if cached_html:
            return cached_html  # return the page immediately if it's cached
    recap_context = get_recap_context(asofdate)
    member_info_context = get_memberinfo()
    featured_event_context = get_featured_event_context()
    notification = get_notification()
    context = {
        "distances": recap_context.distances,
        "recap_type": recap_context.type,
        "recap_event": recap_context.event,
        "recap_race_logo_slug": recap_context.race_logo_slug,
        "recap_results": recap_context.results,
        "memberinfo": member_info_context,
        "featured_event": featured_event_context.event,
        "featured_race_logo_slug": featured_event_context.race_logo_slug,
        "featured_event_data": featured_event_context.data,
        "future_events": featured_event_context.future_events,
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


def get_recap_context(asofdate):
    allResults = Result.objects.all()
    if not allResults.exists():
        return RecapContext()
    last_race_day_events = get_last_race_day_events(allResults, asofdate)
    recap_type = get_recap_type(last_race_day_events)
    distances = get_distances(last_race_day_events)
    recap_event = get_recap_event(last_race_day_events, recap_type, distances)
    race_logo_slug = utils.get_race_logo_slug(recap_event.race.slug)
    recap_results = get_recap_results(recap_event, recap_type)
    return RecapContext(recap_results, recap_event, recap_type, distances, race_logo_slug)


def get_last_race_day_events(allResults, asofdate):
    if not allResults.exists():
        return
    if asofdate:
        maxdate = datetime.strptime(asofdate, "%Y-%m-%d")
        date_of_last_event = (
            allResults.filter(event__date__lte=maxdate).order_by("-event__date")[:1][0].event.date
        )
    else:
        date_of_last_event = allResults.order_by("-event__date")[:1][0].event.date
    last_race = (
        allResults.filter(event__date=date_of_last_event).order_by("-event__date")[:1][0].event.race
    )
    last_race_day_event_ids = (
        Result.objects.filter(event__race=last_race, event__date__year=date_of_last_event.year)
        .values_list("event", flat=True)
        .distinct()
    )
    last_race_day_events = Event.objects.filter(id__in=last_race_day_event_ids).order_by(
        "-date", "-distance__km"
    )
    return last_race_day_events


def get_recap_results(recap_event, recap_type):
    if recap_type == "relay":
        recap_results = get_recap_results_relay(recap_event)
    elif recap_type == "combined":
        recap_results = get_recap_results_combined(recap_event)
    elif recap_type == "endurrun":
        recap_results = get_recap_results_endurrun(recap_event)
    else:
        recap_results = get_recap_results_standard(recap_event)
    return recap_results


def get_recap_results_relay(recap_event):
    # TODO calling other view functions and indices has code smell refactor
    relay_records = shared.get_relay_records(year=recap_event.date.year)
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
    recap_results = view_recap.index(request, year, race_slug, distance_slug, individual_only=True)
    return recap_results


def get_recap_results_endurrun(recap_event):
    recap_results = Endurrunrecap(recap_event)
    return recap_results


def get_recap_results_standard(recap_event):
    event_results = Result.objects.filter(event=recap_event)
    hasmasters = Result.objects.hasmasters(recap_event)
    distance_slug = recap_event.distance.slug
    recap_results = view_recap.get_individual_results(
        recap_event, event_results, hasmasters, distance_slug
    )
    return recap_results


def get_recap_event(last_race_day_events, recap_type, distances):
    """Choose which event to use for a recap"""
    distance_slugs = [x.slug for x in distances]
    if recap_type == "relay" and "2_5-km" in distance_slugs:
        recap_event = last_race_day_events.filter(distance__slug="2_5-km")[0]
    else:
        recap_event = last_race_day_events[0]
    return recap_event


def get_recap_type(last_race_day_events):
    if not last_race_day_events.exists():
        return
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
    if last_race_day_events[0].race.slug == "endurrun":
        recap_type = "endurrun"
    return recap_type


def get_distances(last_race_day_events):
    if not last_race_day_events.exists():
        return
    distances = [x.distance for x in last_race_day_events]
    return distances


def get_memberinfo():
    members = (
        Rwmember.objects.filter(active=True)
        .exclude(photourl=None)
        .exclude(photourl="")
        .order_by("?")
    )
    if not members.exists():
        return MemberInfoContext()
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
    MemberInfoContext(member, racing_since, km, fivek_pb, tenk_pb)
    return MemberInfoContext(member, racing_since, km, fivek_pb, tenk_pb)


def get_featured_event_context():
    events = Event.objects.all()
    if not events.exists():
        return FeaturedEventContext()
    event = get_featured_event()
    race_logo_slug = ""
    if event:
        race_logo_slug = utils.get_race_logo_slug(event.race.slug)
    return FeaturedEventContext(
        event, get_event_data(event), get_future_events(event), race_logo_slug
    )


def get_featured_event():
    featured_event = None
    try:
        featured_event_id = int(Config.objects.get(name="homepage_featured_event_id").value)
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


def get_event_data(event):
    if not event:
        return None
    previous_event = (
        Event.objects.filter(race=event.race, distance=event.distance)
        .exclude(id=event.id)
        .order_by("-date")
        .first()
    )
    previous_event_recap = get_recap_results_standard(previous_event)
    featured_event_records = shared.get_race_records(
        event.race, event.distance, individual_only=True
    )
    event_data = []
    for i in featured_event_records:
        row = UpcomingEvent()
        row.event = event
        row.demographic = i.place
        row.record_athlete = i.athlete
        row.record_member = i.member
        row.record_time = i.guntime
        row.record_year = i.year
        recap_row = 0
        if "Master" in row.demographic:
            recap_row = 3
        if "Female" in row.demographic:
            row.last_year_winning_athlete = previous_event_recap[recap_row].female_athlete
            row.last_year_winning_member = previous_event_recap[recap_row].female_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].female_time
        else:
            row.last_year_winning_athlete = previous_event_recap[recap_row].male_athlete
            row.last_year_winning_member = previous_event_recap[recap_row].male_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].male_time
        event_data.append(row)
    return event_data


def get_future_events(event):
    today = datetime.today()
    future_events = []
    dbfuture_events = Event.objects.filter(date__gte=today).order_by("date", "-distance__km")
    upcoming_races_count_object = Config.objects.filter(
        name="homepage_upcoming_races_count"
    ).first()
    upcoming_races_count = (
        int(upcoming_races_count_object.value) if upcoming_races_count_object else 5
    )

    exclude_events_objects = Config.objects.filter(name="homepage_upcoming_exclude_events").first()
    exclude_events_str = exclude_events_objects.value.split(",") if exclude_events_objects else []
    exclude_events = [int(x) for x in exclude_events_str]

    races_seen = []
    for i in dbfuture_events:
        if i.id in exclude_events:
            continue
        if len(races_seen) == upcoming_races_count:
            if i.race not in races_seen:
                break
        if i == event:
            continue
        event_result_count = Result.objects.filter(event=i).count()
        if event_result_count > 0:
            continue
        numresults = Result.objects.filter(event__race=i.race, event__distance=i.distance).count()
        event_data = False
        if numresults > 0:
            event_data = get_event_data(i)
        race_logo_slug = utils.get_race_logo_slug(i.race.slug)
        future_events.append((i, event_data, race_logo_slug))
        if i.race not in races_seen:
            races_seen.append(i.race)
    return future_events


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


class Endurrunrecap:
    def __init__(self, event):
        self.year = event.date.year
        self.distance_slug = event.distance.slug
        self.endurrun_stages = {
            "half-marathon": 1,
            "15-km": 2,
            "30-km": 3,
            "10-mi": 4,
            "25_6-km": 5,
            "10-km": 6,
            "marathon": 7,
        }
        self.stage_number = self.endurrun_stages.get(self.distance_slug)
        self.ultimate_suffix = "after Stage {}".format(self.stage_number)
        if self.stage_number == 7:
            self.ultimate_suffix += " (Final)"
        self.top_female = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("Female",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0:3]
        self.top_male = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("Male",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0:3]
        self.top_f_masters = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("F-Masters",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0]
        self.top_m_masters = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("M-Masters",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0]

    def __str__(self):
        return "year={}, ultimate_suffix={}".format(self.year, self.ultimate_suffix)
