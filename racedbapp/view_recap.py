from collections import namedtuple

from django.shortcuts import render

from .models import Endurraceresult, Event, Prime, Result, Teamresult
from .shared.endurrun import get_member_endurrace
from .shared.shared import get_membership

namediresult = namedtuple(
    "ni",
    [
        "place",
        "female_athlete",
        "female_time",
        "female_member_slug",
        "male_athlete",
        "male_time",
        "male_member_slug",
    ],
)


def index(request, year, race_slug, distance_slug, individual_only=False):
    if distance_slug == "combined":
        event = False
        results = Endurraceresult.objects.filter(year=year).order_by("guntime")
        hasmasters = Endurraceresult.objects.hasmasters(year)
        team_results = []
    else:
        event = Event.objects.get(
            race__slug=race_slug, distance__slug=distance_slug, date__icontains=year
        )
        results = Result.objects.filter(event_id=event.id)
        hasmasters = Result.objects.hasmasters(event)
        team_results = Teamresult.objects.of_event(event)
    individual_results = get_individual_results(
        event, results, hasmasters, distance_slug, year=year
    )
    if individual_only:
        return individual_results
    hill_results = False
    if race_slug == "baden-road-races" and distance_slug == "7-mi":
        hill_results = []
        rank = "1st OA"
        try:
            male_prime = Prime.objects.filter(event=event, gender="M").order_by("time", "place")[
                :1
            ][0]
        except Exception:
            hill_results = False
        else:
            male_result = results.get(place=male_prime.place)
            male_member_slug = None
            male_member = male_result.rwmember
            if male_member:
                male_member_slug = male_member.slug
            female_prime = Prime.objects.filter(event=event, gender="F").order_by("time", "place")[
                :1
            ][0]
            female_result = results.get(place=female_prime.place)
            female_member_slug = None
            female_member = female_result.rwmember
            if female_member:
                female_member_slug = female_member.slug
            hill_results.append(
                namediresult(
                    rank,
                    female_result.athlete,
                    female_prime.time,
                    female_member_slug,
                    male_result.athlete,
                    male_prime.time,
                    male_member_slug,
                )
            )
    context = {
        "event": event,
        "distance_slug": distance_slug,
        "year": year,
        "individual_results": individual_results,
        "team_results": list(team_results),
        "hill_results": hill_results,
        "nomenu": True,
    }

    return render(request, "racedbapp/recap.html", context)


def get_individual_results(event, results, hasmasters, distance_slug, year=False):
    membership = get_membership()
    individual_results = []
    female_results = list(results.filter(gender="F")[0:3])
    male_results = list(results.filter(gender="M")[0:3])
    for i in range(1, 4):
        if i == 1:
            rank = "1st OA"
        elif i == 2:
            rank = "2nd OA"
        elif i == 3:
            rank = "3rd OA"

        if len(female_results) >= i:
            female_time = female_results[i - 1].guntime
            female_member_slug = None
            if distance_slug != "combined":
                female_member = female_results[i - 1].rwmember
            else:
                female_member = get_member_endurrace(female_results[i - 1], membership)
            if female_member:
                female_member_slug = female_member.slug
            female_athlete = female_results[i - 1].athlete
        else:
            female_athlete = female_time = female_member_slug = None

        if len(male_results) >= i:
            male_time = male_results[i - 1].guntime
            male_member_slug = None
            if distance_slug != "combined":
                male_member = male_results[i - 1].rwmember
            else:
                male_member = get_member_endurrace(male_results[i - 1], membership)
            if male_member:
                male_member_slug = male_member.slug
            male_athlete = male_results[i - 1].athlete
        else:
            male_athlete = male_time = male_member_slug = None

        individual_results.append(
            namediresult(
                rank,
                female_athlete,
                female_time,
                female_member_slug,
                male_athlete,
                male_time,
                male_member_slug,
            )
        )
    if hasmasters:
        if distance_slug == "combined":
            top_masters = Endurraceresult.objects.topmasters(year)
            female_member_slug = male_member_slug = None
            female_member = get_member_endurrace(top_masters.female_result, membership)
            if female_member:
                female_member_slug = female_member.slug
            male_member = get_member_endurrace(top_masters.male_result, membership)
            if male_member:
                male_member_slug = male_member.slug
            new_top_masters = namediresult(
                top_masters.place,
                top_masters.female_athlete,
                top_masters.female_time,
                female_member_slug,
                top_masters.male_athlete,
                top_masters.male_time,
                male_member_slug,
            )
            individual_results.append(new_top_masters)
        else:
            individual_results.append(Result.objects.topmasters(event))
    return individual_results
