import datetime
import urllib
from collections import namedtuple
from datetime import timedelta

from django import db
from django.db.models import Avg, Count, Min, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import render

from . import utils
from .models import *


def index(request, year, race_slug, distance_slug, team_category_slug):
    event_parameters = "{}/{}/{}".format(year, race_slug, distance_slug)
    namedteamresult = namedtuple(
        "ntr", (["team_place", "team_name", "total_time", "avg_time", "athletes"])
    )
    namedteamathlete = namedtuple(
        "nta",
        (["athlete_team_place", "athlete_name", "athlete_time", "counts", "estimated"]),
    )
    event = Event.objects.get(
        race__slug=race_slug, distance__slug=distance_slug, date__icontains=year
    )
    dohill = False
    if race_slug == "baden-road-races" and distance_slug == "7-mi":
        dohill = True
    dorelay = False
    if race_slug == "laurier-loop" and distance_slug == "2_5-km":
        if Relay.objects.filter(event=event).count() > 0:
            dorelay = True
    dowheelchair = False
    wheelchair_results = Wheelchairresult.objects.filter(event=event)
    if wheelchair_results.count() > 0:
        dowheelchair = True
    try:
        team_category = Teamcategory.objects.get(slug=team_category_slug)
    except:
        raise Http404("Team category not found")
    present_team_categories = Teamresult.objects.filter(event_id=event.id).values_list(
        "team_category__name", flat=True
    )
    present_team_categories = set(sorted(present_team_categories))
    team_categories = Teamcategory.objects.filter(name__in=present_team_categories)
    results = Teamresult.objects.filter(
        event_id=event.id, team_category_id=team_category.id
    ).order_by("team_place", "athlete_team_place")
    teams = Teamresult.objects.filter(
        event_id=event.id, team_category_id=team_category.id, athlete_team_place=1
    ).values_list("team_name", flat=True)
    team_results = []
    team_place = 1
    for team in teams:
        total_time = utils.truncate_time(
            results.filter(team_name=team)
            .filter(counts=True)
            .aggregate(Sum("athlete_time"))["athlete_time__sum"]
        )
        raw_avg_time = (
            results.filter(team_name=team)
            .filter(counts=True)
            .aggregate(Avg("athlete_time"))["athlete_time__avg"]
        )
        avg_time = raw_avg_time - timedelta(microseconds=raw_avg_time.microseconds)
        rawathletes = results.filter(team_name=team)
        athletes = []
        for athlete in rawathletes:
            thistime = utils.truncate_time(athlete.athlete_time)
            athletes.append(
                namedteamathlete(
                    athlete.athlete_team_place,
                    athlete.athlete_name,
                    thistime,
                    athlete.counts,
                    athlete.estimated,
                )
            )
        ntr = namedteamresult(team_place, team, total_time, avg_time, athletes)
        team_results.append(ntr)
        team_place += 1

    context = {
        "event": event,
        "event_parameters": event_parameters,
        "team_category": team_category,
        "team_categories": team_categories,
        "team_results": team_results,
        "dohill": dohill,
        "dowheelchair": dowheelchair,
        "dorelay": dorelay,
    }
    # print(len(db.connection.queries))   # number of sql queries that happened
    return render(request, "racedbapp/event_team.html", context)
