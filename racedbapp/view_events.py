import urllib
from collections import namedtuple
from datetime import timedelta

from django import db
from django.db.models import Count, Min
from django.http import Http404, HttpResponse
from django.shortcuts import render

from .shared import shared
from racedbapp.shared.types import Choice, Filter
from .models import *


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    events = (
        Event.objects.select_related()
        .annotate(num_events=Count("result"))
        .filter(num_events__gte=1)
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
    if "race" in qstring:
        race_slug = qstring["race"][0]
        race_name = shared.get_race_by_slug_or_false(race_slug)
        if not race_name:
            raise Http404(f"No race found for slug '{race_slug}'")
        races = shared.create_samerace_list(race_name)
        events = events.filter(race__in=races)
        yearfilter_events = yearfilter_events.filter(race__in=races)
        distancefilter_events = distancefilter_events.filter(race__in=races)
        racefilter = "&race={}".format(race_slug)
    else:
        race_id = "All"
        race_name = "All"
        racefilter = ""
    if "distance" in qstring:
        distance_slug = qstring["distance"][0]
        try:
            distance_id = Distance.objects.get(slug=distance_slug).id
        except:
            raise Http404("Invalid distance ({})".format(distance_slug))
        events = events.filter(distance_id=distance_id)
        yearfilter_events = yearfilter_events.filter(distance_id=distance_id)
        racefilter_events = racefilter_events.filter(distance_id=distance_id)
        distancefilter = "&distance={}".format(distance_slug)
        distance_name = Distance.objects.get(id=distance_id)
    else:
        distance_id = "All"
        distance_name = "All"
        distancefilter = ""
    yearfilters = getfilter("year", racefilter, distancefilter, yearfilter_events, year)
    racefilters = getfilter(
        "race", yearfilter, distancefilter, racefilter_events, race_name
    )
    distancefilters = getfilter(
        "distance", yearfilter, racefilter, distancefilter_events, distance_name
    )
    malewinnersdict, femalewinnersdict = shared.getwinnersdict()
    namedevent = namedtuple(
        "ne",
        [
            "year",
            "race_name",
            "race_slug",
            "distance_name",
            "distance_slug",
            "femalewinner",
            "femaletime",
            "femalemember",
            "malewinner",
            "maletime",
            "malemember",
            "flickrsetid",
        ],
    )
    member_dict = shared.get_member_dict()
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
        namedevents.append(
            namedevent(
                e.date.year,
                e.race.shortname,
                e.race.slug,
                e.distance.name,
                e.distance.slug,
                femalewinnersdict[e.id].athlete,
                femaletime,
                femalemember,
                malewinnersdict[e.id].athlete,
                maletime,
                malemember,
                e.flickrsetid,
            )
        )
    events = namedevents
    context = {
        "events": events,
        "yearfilters": yearfilters,
        "racefilters": racefilters,
        "distancefilters": distancefilters,
        "malewinnersdict": malewinnersdict,
        "femalewinnersdict": femalewinnersdict,
    }
    return render(request, "racedbapp/events.html", context)


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
        old_races = list(Samerace.objects.values_list("old_race", flat=True))
        new_races = list(Samerace.objects.values_list("current_race", flat=True))
        for e in filter_events:
            if e.race.id in old_races:
                thisrace = Samerace.objects.get(old_race=e.race).current_race
            else:
                thisrace = e.race
            newqs = "{}&race={}{}".format(filter1, thisrace.slug, filter2)
            if newqs[0] == "&":
                newqs = "?{}".format(newqs[1:])
            # start append old names
            if thisrace.id in new_races:
                old_names = []
                for i in Samerace.objects.filter(current_race=thisrace):
                    old_names.append(i.old_race.name)
                old_names_str = ", ".join(old_names)
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
