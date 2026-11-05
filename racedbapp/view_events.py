import urllib
from collections import namedtuple

from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from racedbapp.shared.tracing import tracer
from racedbapp.shared.types import Choice, Filter

from .models import Distance, Event, Result, Samerace
from .shared import cache_lock, shared

CACHEABLE_PARAMS = {"year", "race", "distance"}


def index(request):
    if request.method != "GET":
        return _render(request)
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    bypass = _cache_bypass(qstring)
    _validate_qstring(qstring)
    cache_key = _cache_key(qstring)
    if bypass:
        # cache=false: always cold render, key unchanged (test cache buster).
        return _render(request)
    cached = cache_lock.get(cache_key)
    if cached is not None:
        return cached
    return cache_lock.get_or_render(cache_key, lambda: _render(request))


def _validate_qstring(qstring):
    """404 on anything but year/race/distance, each given at most once.

    The single exception is cache=false, which requests an uncached render.
    """
    allowed = CACHEABLE_PARAMS | {"cache"}
    bad = [k for k in qstring if k not in allowed]
    if bad or any(len(values) != 1 for values in qstring.values()):
        raise Http404("Invalid query parameter")
    if "cache" in qstring and qstring["cache"][0] != "false":
        raise Http404("Invalid cache parameter")


def _cache_bypass(qstring):
    """True when the query string asks for an uncached render (cache=false)."""
    return qstring.get("cache", [""])[0] == "false"


def _cache_key(qstring):
    """Cache key over the recognized params, absent ones as 'all'."""
    return "events.{}.{}.{}".format(
        qstring.get("year", ["all"])[0],
        qstring.get("race", ["all"])[0],
        qstring.get("distance", ["all"])[0],
    )


def _render(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    events = (
        Event.objects.select_related("race", "distance", "sequel")
        .filter(Exists(Result.objects.filter(event=OuterRef("pk"))))
        .order_by("-date", "-distance__km")
    )
    yearfilter_events = events
    racefilter_events = events.order_by("race__name")
    distancefilter_events = events.order_by("distance__km")
    if "year" in qstring:
        year = int(qstring["year"][0])
        events = events.filter(date__year=year)
        racefilter_events = racefilter_events.filter(date__year=year)
        distancefilter_events = distancefilter_events.filter(date__year=year)
        yearfilter = "&year={}".format(year)
    else:
        year = "All"
        yearfilter = ""
    race_ids = None
    if "race" in qstring:
        race_slug = qstring["race"][0]
        race_name = shared.get_race_by_slug_or_false(race_slug)
        if not race_name:
            raise Http404(f"No race found for slug '{race_slug}'")
        races = shared.create_samerace_list(race_name)
        race_ids = {r.id for r in races}
        events = events.filter(race__in=races)
        yearfilter_events = yearfilter_events.filter(race__in=races)
        distancefilter_events = distancefilter_events.filter(race__in=races)
        racefilter = "&race={}".format(race_slug)
    else:
        race_name = "All"
        racefilter = ""
    distance_id = "All"
    if "distance" in qstring:
        distance_slug = qstring["distance"][0]
        try:
            distance_id = Distance.objects.get(slug=distance_slug).id
        except Exception:
            raise Http404("Invalid distance ({})".format(distance_slug))
        events = events.filter(distance_id=distance_id)
        yearfilter_events = yearfilter_events.filter(distance_id=distance_id)
        racefilter_events = racefilter_events.filter(distance_id=distance_id)
        distancefilter = "&distance={}".format(distance_slug)
        distance_name = Distance.objects.get(id=distance_id)
    else:
        distance_name = "All"
        distancefilter = ""
    with tracer.start_as_current_span("events: fetch"):
        events = list(events)
        # All three dropdowns derive from the one evaluated `events` list:
        # each is `events` minus its own filter's condition.
        has_race = race_ids is not None
        has_distance = distance_id != "All"

        def _subset(check_race, check_distance):
            subset = []
            for e in events:
                if check_race and e.race_id not in race_ids:
                    continue
                if check_distance and e.distance_id != distance_id:
                    continue
                subset.append(e)
            return subset

        yearfilter_events = _subset(has_race, has_distance)
        racefilter_events = _subset(False, has_distance)
        distancefilter_events = _subset(has_race, False)
    with tracer.start_as_current_span("events: year dropdown"):
        yearfilters = getfilter("year", racefilter, distancefilter, yearfilter_events, year)
    with tracer.start_as_current_span("events: race dropdown"):
        racefilters = getfilter("race", yearfilter, distancefilter, racefilter_events, race_name)
    with tracer.start_as_current_span("events: distance dropdown"):
        distancefilters = getfilter(
            "distance", yearfilter, racefilter, distancefilter_events, distance_name
        )
    with tracer.start_as_current_span("events: winners dicts"):
        malewinnersdict, femalewinnersdict = shared.getwinnersdict()
    with tracer.start_as_current_span("events: member dict"):
        member_dict = shared.get_member_dict()
    with tracer.start_as_current_span("events: event rows"):
        namedevents = _build_event_rows(events, femalewinnersdict, malewinnersdict, member_dict)
    events = namedevents
    context = {
        "events": events,
        "yearfilters": yearfilters,
        "racefilters": racefilters,
        "distancefilters": distancefilters,
        "malewinnersdict": malewinnersdict,
        "femalewinnersdict": femalewinnersdict,
    }
    with tracer.start_as_current_span("events: template render"):
        return render(request, "racedbapp/events.html", context)


def _build_event_rows(events, femalewinnersdict, malewinnersdict, member_dict):
    namedevent = namedtuple(
        "ne",
        [
            "year",
            "race_name",
            "race_slug",
            "distance",
            "femalewinner",
            "femaletime",
            "femalemember",
            "malewinner",
            "maletime",
            "malemember",
            "flickrsetid",
            "url",
        ],
    )
    namedevents = []
    for e in events:
        femalewinner = femalewinnersdict[e.id]
        femaletime = femalewinner.guntime
        femalemember = False
        if femalewinner.athlete.lower() in member_dict:
            femalemember = member_dict[femalewinner.athlete.lower()]
        malewinner = malewinnersdict[e.id]
        maletime = malewinner.guntime
        malemember = False
        if malewinner.athlete.lower() in member_dict:
            malemember = member_dict[malewinner.athlete.lower()]
        shared.set_distance_display_name(e.distance, getattr(e, "sequel", None))
        url_args = [e.date.year, e.race.slug, e.distance.slug]
        if e.distance.sequel_slug:
            url_args.append(e.distance.sequel_slug)
        url = reverse("event", args=url_args)
        namedevents.append(
            namedevent(
                e.date.year,
                e.race.shortname,
                e.race.slug,
                e.distance,
                femalewinnersdict[e.id].athlete,
                femaletime,
                femalemember,
                malewinnersdict[e.id].athlete,
                maletime,
                malemember,
                e.flickrsetid,
                url,
            )
        )
    return namedevents


def getfilter(filtername, filter1, filter2, filter_events, current):
    curfilters = filter1 + filter2
    if len(curfilters) > 0:
        if curfilters[0] == "&":
            curfilters = "?{}".format(curfilters[1:])
    choices = [
        Choice("All", "/events/{}".format(curfilters)),
    ]
    if filtername == "year":
        for e in filter_events:
            thisfilter = Choice(
                e.date.year,
                "/events/?year={}{}{}".format(e.date.year, filter1, filter2),
            )
            if thisfilter not in choices:
                choices.append(thisfilter)
    elif filtername == "race":
        # Samerace is a tiny table: load it once instead of querying per event.
        sameraces = list(Samerace.objects.select_related("old_race", "current_race"))
        old_to_current = {s.old_race_id: s.current_race for s in sameraces}
        current_race_ids = {s.current_race_id for s in sameraces}
        old_names_by_current = {}
        for s in sameraces:
            old_names_by_current.setdefault(s.current_race_id, []).append(s.old_race.name)
        for e in filter_events:
            if e.race.id in old_to_current:
                thisrace = old_to_current[e.race.id]
            else:
                thisrace = e.race
            newqs = "{}&race={}{}".format(filter1, thisrace.slug, filter2)
            if newqs[0] == "&":
                newqs = "?{}".format(newqs[1:])
            # start append old names
            if thisrace.id in current_race_ids:
                old_names_str = ", ".join(old_names_by_current[thisrace.id])
                display = "{} ({})".format(thisrace.name, old_names_str)
                if not isinstance(current, str):
                    if thisrace.name == current.name:
                        current = display
                thisfilter = Choice(display, "/events/{}".format(newqs))
            else:
                thisfilter = Choice(thisrace.name, "/events/{}".format(newqs))
            # end append old names
            if thisfilter not in choices:
                choices.append(thisfilter)
    elif filtername == "distance":
        for e in filter_events:
            newqs = "{}{}&distance={}".format(filter1, filter2, e.distance.slug)
            if newqs[0] == "&":
                newqs = "?{}".format(newqs[1:])
            thisfilter = Choice(e.distance.name, "/events/{}".format(newqs))
            if thisfilter not in choices:
                choices.append(thisfilter)
    choices = [x for x in choices if x.name != current]
    afilter = Filter(current, choices)
    return afilter
