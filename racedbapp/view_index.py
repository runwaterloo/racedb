from django.shortcuts import render
from django.http import HttpResponse

# from django.db.models import Min, Q
# from django import db
from collections import namedtuple
import random
import urllib
import simplejson
from . import view_recap, view_member, view_shared
from datetime import datetime
from .models import Config, Event, Result, Rwmember

named_future_event = namedtuple("nfe", ["event", "race", "distance", "records"])

named_event = namedtuple("ne", ["date", "city"])
named_race = namedtuple("nr", ["name", "shortname", "slug"])
named_distance = namedtuple("nd", ["name", "slug", "km"])


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    lastraceday = get_lastraceday()
    recap_event = random.choice(lastraceday)
    memberinfo = get_memberinfo()
    featured_event = get_featured_event()
    featured_event_records = get_featured_event_records(featured_event)
    future_events = get_future_events(featured_event)
    context = {
        "lastraceday": lastraceday,
        "recap_event": recap_event,
        "memberinfo": memberinfo,
        "featured_event": featured_event,
        "featured_event_records": featured_event_records,
        "future_events": future_events,
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
        return render(request, "racedbapp/index.html", context)


def get_lastraceday():
    lastraceday = []
    named_lastraceday = namedtuple("nl", ["event", "recap"])
    date_of_last_event = Result.objects.all().order_by("-event__date")[:1][0].event.date
    last_day_events = Event.objects.filter(date=date_of_last_event).order_by(
        "-distance"
    )
    for lde in last_day_events:
        event_results = Result.objects.filter(event=lde)
        hasmasters = Result.objects.hasmasters(lde)
        distance_slug = lde.distance.slug
        individual_recap = view_recap.get_individual_results(
            lde, event_results, hasmasters, distance_slug
        )
        lastraceday.append(named_lastraceday(lde, individual_recap))
    return lastraceday


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
    member = (
        Rwmember.objects.filter(active=True)
        .exclude(photourl=None)
        .exclude(photourl="")
        .order_by("?")[:1][0]
    )
    member_results, km = view_member.get_memberresults(member)
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


def get_featured_event_records(featured_event):
    featured_event_records = None
    if featured_event:
        featured_event_records = view_shared.getracerecords(
            featured_event.race, featured_event.distance, individual_only=True
        )
    return featured_event_records
