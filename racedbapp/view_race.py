import urllib
from collections import namedtuple

from django.db.models import Q
from django.http import Http404
from django.shortcuts import render

import racedbapp.shared.endurrun
from racedbapp.shared.types import Choice, Filter

from .models import Distance, Endurraceresult, Event, Prime, Result
from .shared import shared, utils


def index(request, race_slug, distance_slug):
    namedyear = namedtuple("ny", ["year", "race_slug"])
    namedresult = namedtuple(
        "nr",
        [
            "place",
            "guntime",
            "athlete",
            "year",
            "category",
            "city",
            "extra",
            "age",
            "race_slug",
            "member",
        ],
    )
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    if "filter" in qstring:
        filter_choice = qstring["filter"][0]
    else:
        filter_choice = ""
    if "division" in qstring:
        division_choice = qstring["division"][0]
    else:
        division_choice = "Ultimate"
    divisions = ["Ultimate", "Sport", "Relay", "Guest", "All"]
    race = shared.get_race_by_slug_or_false(race_slug)
    if not race:
        raise Http404()
    races = shared.create_samerace_list(race)
    distance_ids = Event.objects.filter(race=race).values_list("distance", flat=True).distinct()
    distances = Distance.objects.filter(pk__in=set(distance_ids)).order_by("-km")
    distances = list(distances)
    if distances and race_slug == "endurrun":  # order by stages if endurrun
        distances = [
            distances[3],
            distances[5],
            distances[1],
            distances[4],
            distances[2],
            distances[6],
            distances[0],
        ]
    if race and race.slug == "endurrace":
        nameddistance = namedtuple("nd", ["name", "slug", "km"])
        combined_distance = nameddistance("Combined", "combined", 13)
        distances = list(reversed(distances))
        distances.insert(0, combined_distance)
    years = []
    if race and distance_slug == "combined":
        distance = combined_distance
        rawresults = Endurraceresult.objects.all()
        numyears = rawresults.order_by("-year").values_list("year", flat=True).distinct()
        for y in numyears:
            years.append(namedyear(y, "endurrace"))
    else:
        distance = shared.get_distance_by_slug_or_false(distance_slug)
        if not distance:
            raise Http404()
        rawresults = Result.objects.select_related().filter(
            event__race__in=races, event__distance=distance
        )
        dates = (
            rawresults.order_by("-event__date")
            .values_list("event__date", "event__race__slug")
            .distinct()
        )
        for d in dates:
            years.append(namedyear(d[0].year, d[1]))
        # dates = rawresults.order_by('-event__date').values_list('event__date', flat=True).distinct()
        # years = sorted([ x.year for x in dates ], reverse=True)

    records, team_records, hill_records = shared.get_race_records(race, distance, division_choice)
    record_divs = [x.place for x in records]
    results = rawresults.order_by("guntime")
    if race and race.slug == "endurrun" and division_choice != "All":
        results = results.filter(division=division_choice)
    if filter_choice in ("Female", "F-Masters"):
        results = results.filter(gender="F")
    if filter_choice in ("Male", "M-Masters"):
        results = results.filter(gender="M")
    if "Masters" in filter_choice:
        if race_slug == "endurrun":
            results = results.filter(age__gte=40)
        elif race_slug == "endurrace":
            results = results.filter(category__ismasters=True)
        else:
            results = results.filter(Q(category__ismasters=True) | Q(age__gte=40))
    results = results[:50]
    final_results = []
    count = 1
    membership = shared.get_membership()
    for result in results:
        guntime = result.guntime
        if guntime.total_seconds() >= 35600:
            continue
        if distance.slug == "combined":
            year = result.year
            extra = [result.fivektime, result.eightktime]
            age = ""
        else:
            year = result.event.date.year
            extra = False
            if result.age:
                age = result.age
            else:
                age = ""
        if race_slug == "endurrace":
            result_race_slug = "endurrace"
        else:
            result_race_slug = result.event.race.slug
        if distance_slug == "combined":
            member = racedbapp.shared.endurrun.get_member_endurrace(result, membership)
        else:
            member = shared.get_member(result, membership)
        final_results.append(
            namedresult(
                count,
                guntime,
                result.athlete,
                year,
                result.category,
                result.city,
                extra,
                age,
                result_race_slug,
                member,
            )
        )
        count += 1
    if race and race.slug == "endurrun" and division_choice != "Ultimate":
        choices = [
            Choice(
                "",
                "/race/{}/{}/?division={}".format(race_slug, distance_slug, division_choice),
            ),
            Choice(
                "Female",
                "/race/{}/{}/?division={}&filter=Female".format(
                    race_slug, distance_slug, division_choice
                ),
            ),
            Choice(
                "Male",
                "/race/{}/{}/?division={}&filter=Male".format(
                    race_slug, distance_slug, division_choice
                ),
            ),
        ]
        if "Masters Female" in record_divs and "Masters Male" in record_divs:
            choices.append(
                Choice(
                    "Masters",
                    "/race/{}/{}/?division={}&filter=Masters".format(
                        race_slug, distance_slug, division_choice
                    ),
                )
            )
        if "Masters Female" in record_divs:
            choices.append(
                Choice(
                    "F-Masters",
                    "/race/{}/{}/?division={}&filter=F-Masters".format(
                        race_slug, distance_slug, division_choice
                    ),
                )
            )
        if "Masters Male" in record_divs:
            choices.append(
                Choice(
                    "M-Masters",
                    "/race/{}/{}/?division={}&filter=M-Masters".format(
                        race_slug, distance_slug, division_choice
                    ),
                )
            )
    else:
        choices = [
            Choice("", "/race/{}/{}".format(race_slug, distance_slug)),
            Choice("Female", "/race/{}/{}/?filter=Female".format(race_slug, distance_slug)),
            Choice("Male", "/race/{}/{}/?filter=Male".format(race_slug, distance_slug)),
        ]
        if "Masters Female" in record_divs and "Masters Male" in record_divs:
            choices.append(
                Choice(
                    "Masters",
                    "/race/{}/{}/?filter=Masters".format(race_slug, distance_slug),
                )
            )
        if "Masters Female" in record_divs:
            choices.append(
                Choice(
                    "F-Masters",
                    "/race/{}/{}/?filter=F-Masters".format(race_slug, distance_slug),
                )
            )
        if "Masters Male" in record_divs:
            choices.append(
                Choice(
                    "M-Masters",
                    "/race/{}/{}/?filter=M-Masters".format(race_slug, distance_slug),
                )
            )
    choices = [x for x in choices if x.name != filter_choice]
    resultfilter = Filter(filter_choice, choices)
    if race_slug == "baden-road-races" and distance_slug == "7-mi":
        hill_results = get_hill_results()
    else:
        hill_results = False
    race_logo_slug = utils.get_race_logo_slug(race.slug)
    context = {
        "race": race,
        "race_logo_slug": race_logo_slug,
        "distance": distance,
        "distances": distances,
        "years": years,
        "resultfilter": resultfilter,
        "results": final_results,
        "records": records,
        "team_records": team_records,
        "hill_results": hill_results,
        "hill_records": hill_records,
        "divisions": divisions,
        "division_choice": division_choice,
    }
    return render(request, "racedbapp/race.html", context)


def get_hill_results():
    named_hill_result = namedtuple(
        "nhr", ["place", "female_time", "female_result", "male_time", "male_result"]
    )
    results = Result.objects.filter(
        event__race__slug="baden-road-races", event__distance__slug="7-mi"
    )
    hill_results = []
    female_primes = Prime.objects.filter(gender="F").order_by("time", "place")[:10]
    female_primes_dict = {}
    count = 1
    for p in female_primes:
        female_result = results.get(event=p.event, place=p.place)
        female_primes_dict[count] = [p.time, female_result]
        count += 1
    male_primes = Prime.objects.filter(gender="M").order_by("time", "place")[:10]
    male_primes_dict = {}
    count = 1
    for p in male_primes:
        male_result = results.get(event=p.event, place=p.place)
        male_primes_dict[count] = [p.time, male_result]
        count += 1
    for i in range(1, 11):
        female_prime = str(female_primes_dict[i][0]).lstrip("0:")
        male_prime = str(male_primes_dict[i][0]).lstrip("0:")
        hill_results.append(
            named_hill_result(
                i,
                female_prime,
                female_primes_dict[i][1],
                male_prime,
                male_primes_dict[i][1],
            )
        )
    return hill_results
