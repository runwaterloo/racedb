import urllib
from collections import namedtuple

from django.http import Http404
from django.shortcuts import render

import racedbapp.shared.endurrun
from racedbapp.shared.types import Choice, Filter

from .models import Endurraceresult, Event, Result
from .shared import shared


def index(request, year):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    allresults = Result.objects.filter(event__race__slug="endurrace", event__distance__slug="8-km")
    if not allresults:
        raise Http404("No results found for Endurrace.")
    dates = allresults.order_by("-event__date").values_list("event__date", flat=True).distinct()
    years = sorted([x.year for x in dates], reverse=True)
    if not year.isdigit() and year != "latest":
        raise Http404("Invalid year specified for Endurrace.")
    if year == "latest":
        year = max(years)
    else:
        year = int(year)
    if year not in years:
        raise Http404("No results found for Endurrace in the year {}.".format(year))
    years.pop(years.index(year))
    events = Event.objects.filter(race__slug="endurrace", date__icontains=year)
    filter_choice = ""
    if "filter" in qstring:
        filter_choice = qstring["filter"][0]
    combined_results = []
    for event in events:
        event_results = Result.objects.filter(event_id=event.id).order_by("place")
        combined_results.append(event_results)
    hasmasters = Result.objects.hasmasters(events[0])
    genderdict = {}
    categorydict = {}
    namedresult = namedtuple(
        "nr",
        [
            "place",
            "bib",
            "athlete",
            "total_time",
            "category",
            "category_place",
            "category_total",
            "gender_place",
            "fivek_time",
            "eightk_time",
            "city",
            "member",
        ],
    )
    results2 = []
    results1 = Endurraceresult.objects.filter(year=year).order_by("guntime")
    membership = shared.get_membership()
    place = 0
    for result in results1:
        gender_place = ""
        if result.gender not in genderdict:
            if result.gender != "":
                gender_place = 1
                genderdict[result.gender] = 1
        else:
            if result.gender != "":
                gender_place = genderdict[result.gender] + 1
                genderdict[result.gender] = gender_place
        if result.category.name not in categorydict:
            category_place = 1
            categorydict[result.category.name] = 1
        else:
            category_place = categorydict[result.category.name] + 1
            categorydict[result.category.name] = category_place
        place += 1
        if filter_choice == "Female":
            if result.gender != "F":
                continue
        elif filter_choice == "Male":
            if result.gender != "M":
                continue
        elif filter_choice == "Masters":
            if not result.category.ismasters:
                continue
        elif filter_choice == "F-Masters":
            if not result.category.ismasters or result.gender != "F":
                continue
        elif filter_choice == "M-Masters":
            if not result.category.ismasters or result.gender != "M":
                continue
        elif filter_choice != "":
            if result.category.name != filter_choice:
                continue
        member = racedbapp.shared.endurrun.get_member_endurrace(result, membership)
        results2.append(
            namedresult(
                place,
                result.bib,
                result.athlete,
                result.guntime,
                result.category,
                category_place,
                0,
                gender_place,
                result.fivektime,
                result.eightktime,
                result.city,
                member,
            )
        )
    results3 = []
    for result in results2:
        results3.append(
            namedresult(
                result.place,
                result.bib,
                result.athlete,
                result.total_time,
                result.category,
                result.category_place,
                categorydict[result.category.name],
                result.gender_place,
                result.fivek_time,
                result.eightk_time,
                result.city,
                result.member,
            )
        )
    resultfilter = getresultfilter(filter_choice, categorydict, year, hasmasters)
    context = {
        "events": events,
        "year": year,
        "years": years,
        "categorydict": categorydict,
        "resultfilter": resultfilter,
        "results": results3,
    }
    return render(request, "racedbapp/endurrace.html", context)


def getresultfilter(filter_choice, categorydict, year, hasmasters):
    choices = [
        Choice("", "/endurrace/{}".format(year)),
        Choice("Female", "/endurrace/{}/?filter=Female".format(year)),
        Choice("Male", "/endurrace/{}/?filter=Male".format(year)),
    ]
    if hasmasters:
        choices.append(Choice("Masters", "/endurrace/{}/?filter=Masters".format(year)))
        choices.append(Choice("F-Masters", "/endurrace/{}/?filter=F-Masters".format(year)))
        choices.append(Choice("M-Masters", "/endurrace/{}/?filter=M-Masters".format(year)))
    for k, v in sorted(categorydict.items()):
        choices.append(Choice(k, "/endurrace/{}/?filter={}".format(year, k)))
    choices = [x for x in choices if x.name != filter_choice]
    resultfilter = Filter(filter_choice, choices)
    return resultfilter
