from collections import namedtuple
from urllib import parse

from django.db.models import Q
from django.shortcuts import render

from racedbapp.shared.types import Choice, Filter

from .shared import shared
from .models import *

named_distance_record = namedtuple("ndr", ["place", "result", "member"])


def index(request, distance_slug):
    membership = shared.get_membership()
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    topx = int(shared.get_config_value_or_false("distance_topx"))
    topx_filter = False
    if "filter" in qstring:
        topx_filter = qstring["filter"][0]
    distance = shared.get_distance_by_slug_or_false(distance_slug)
    distances = Distance.objects.filter(showrecord=True).order_by("km")
    named_distance_record = namedtuple(
        "ndr", ["female", "male", "masters_female", "masters_male"]
    )
    distance_results = Result.objects.filter(event__distance=distance)
    records = []
    records += get_dist_records(
        "Overall Male", distance_results, "M", False, membership
    )
    records += get_dist_records(
        "Overall Female", distance_results, "F", False, membership
    )
    records += get_dist_records("Masters Male", distance_results, "M", True, membership)
    records += get_dist_records(
        "Masters Female", distance_results, "F", True, membership
    )
    topxresults = get_topxresults(distance, topx, topx_filter, membership)
    resultfilter = get_resultfilter(distance_slug, topx_filter)
    context = {
        "topx": topx,
        "topxresults": topxresults,
        "topx_filter": topx_filter,
        "resultfilter": resultfilter,
        "distance": distance,
        "distances": distances,
        "records": records,
    }
    return render(request, "racedbapp/distance.html", context)


def get_dist_records(place, distance_results, gender, masters, membership):
    distance_records = []
    filtered_results = distance_results.filter(gender=gender)
    if masters:
        filtered_results = filtered_results.filter(
            Q(category__ismasters=True) | Q(age__gte=40)
        )
    record_time = filtered_results.aggregate(min_time=Min("guntime"))["min_time"]
    dbdistance_records = filtered_results.filter(guntime=record_time)
    for d in dbdistance_records:
        member = shared.get_member(d, membership)
        distance_records.append(named_distance_record(place, d, member))
    return distance_records


def get_topxresults(distance, topx, topx_filter, membership):
    named_result = namedtuple("nr", ["result", "member"])
    topxresults = []
    dbresults = Result.objects.select_related().filter(event__distance=distance)
    if topx_filter:
        if topx_filter in ("Female", "F-Masters"):
            dbresults = dbresults.filter(gender="F")
        elif topx_filter in ("Male", "M-Masters"):
            dbresults = dbresults.filter(gender="M")
        if "Masters" in topx_filter:
            dbresults = dbresults.filter(Q(category__ismasters=True) | Q(age__gte=40))
    dbresults = dbresults.order_by("guntime")[:topx]
    for r in dbresults:
        member = shared.get_member(r, membership)
        topxresults.append(named_result(r, member))
    return topxresults


def get_resultfilter(distance_slug, topx_filter):
    if topx_filter:
        current = topx_filter
    else:
        current = ""
    choices = []
    if topx_filter:
        choices.append(Choice("", "/distance/{}/".format(distance_slug)))
    for f in ["Female", "Male", "Masters", "F-Masters", "M-Masters"]:
        if f != topx_filter:
            choices.append(
                Choice(f, "/distance/{}/?filter={}".format(distance_slug, f))
            )
    resultfilter = Filter(current, choices)
    return resultfilter
