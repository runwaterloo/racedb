import urllib
from collections import namedtuple
from datetime import timedelta
from operator import attrgetter

from django.shortcuts import render

from racedbapp.shared.types import Choice, Filter

from .models import Bow, Bowathlete, Category, Event, Result


def index(request, bow_slug):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    bow = Bow.objects.get(slug=bow_slug)
    bows = Bow.objects.all()
    event_ids = eval(Bow.objects.get(slug=bow_slug).events)
    events = Event.objects.filter(id__in=(event_ids)).order_by("date")
    filter_choice = ""
    if "filter" in qstring:
        filter_choice = qstring["filter"][0]
    stop_event = 999999
    phase_choice = "Final Results"
    if "phase" in qstring:
        phase_choice = qstring["phase"][0]
        stop_event = int(phase_choice.split("-")[2])
    results = []
    namedresult = namedtuple(
        "na", ["athlete", "stages", "total_time", "total_seconds", "stage_times"]
    )
    athletes = Bowathlete.objects.filter(bow=bow)
    if filter_choice == "Female":
        athletes = athletes.filter(gender="F")
    elif filter_choice == "Male":
        athletes = athletes.filter(gender="M")
    elif filter_choice == "Masters":
        athletes = athletes.filter(category__ismasters=True)
    elif filter_choice == "F-Masters":
        athletes = athletes.filter(gender="F", category__ismasters=True)
    elif filter_choice == "M-Masters":
        athletes = athletes.filter(gender="M", category__ismasters=True)
    elif filter_choice != "":
        athletes = athletes.filter(category__name=filter_choice)
    hasmasters = True
    category_ids = Bowathlete.objects.filter(bow=bow).values_list("category", flat=True).distinct()
    categories = Category.objects.filter(id__in=(category_ids)).order_by("name")
    all_event_results = []
    events_results_count = []
    for event in events:
        event_results = Result.objects.filter(event=event)
        events_results_count.append(event_results.count())
        event_list = event_results.values_list("athlete", "guntime")
        event_dict = {}
        for i in event_list:
            event_dict[i[0].lower()] = i[1]
        all_event_results.append(event_dict)
    for athlete in athletes:
        stages = 0
        stage_times = []
        total_time = timedelta(seconds=0)
        count = 1
        for er in all_event_results:
            try:
                stage_time = er[athlete.name.lower()]
            except Exception:
                stage_time = ""
            else:
                if count <= stop_event:
                    stages += 1
                    total_time += stage_time
                else:
                    stage_time = ""
            stage_times.append(stage_time)
            count += 1
        if total_time == timedelta(seconds=0):
            total_seconds = 0
            total_time = ""
        else:
            total_seconds = total_time.total_seconds()
        results.append(namedresult(athlete, stages, total_time, total_seconds, stage_times))
    results = sorted(results, key=attrgetter("total_seconds"))
    results = sorted(results, key=attrgetter("stages"), reverse=True)
    resultfilter = getresultfilter(filter_choice, phase_choice, categories, bow_slug, hasmasters)
    phasefilter = getphasefilter(phase_choice, filter_choice, events_results_count, bow_slug)
    context = {
        "events": events,
        "events_results_count": events_results_count,
        "resultfilter": resultfilter,
        "phasefilter": phasefilter,
        "bow": bow,
        "bows": bows,
        "results": results,
    }
    return render(request, "racedbapp/bow.html", context)


def getresultfilter(filter_choice, phase_choice, categories, bow_slug, hasmasters):
    if phase_choice == "Final Results":
        choices = [
            Choice("", "/bow/{}/".format(bow_slug)),
            Choice("Female", "/bow/{}/?filter=Female".format(bow_slug)),
            Choice("Male", "/bow/{}/?filter=Male".format(bow_slug)),
        ]
        if hasmasters:
            choices.append(Choice("Masters", "/bow/{}/?filter=Masters".format(bow_slug)))
            choices.append(Choice("F-Masters", "/bow/{}/?filter=F-Masters".format(bow_slug)))
            choices.append(Choice("M-Masters", "/bow/{}/?filter=M-Masters".format(bow_slug)))
    else:
        choices = [
            Choice("", "/bow/{}/?phase={}".format(bow_slug, phase_choice)),
            Choice(
                "Female",
                "/bow/{}/?filter=Female&phase={}".format(bow_slug, phase_choice),
            ),
            Choice("Male", "/bow/{}/?filter=Male&phase={}".format(bow_slug, phase_choice)),
        ]
        if hasmasters:
            choices.append(
                Choice(
                    "Masters",
                    "/bow/{}/?filter=Masters&phase={}".format(bow_slug, phase_choice),
                )
            )
            choices.append(
                Choice(
                    "F-Masters",
                    "/bow/{}/?filter=F-Masters&phase={}".format(bow_slug, phase_choice),
                )
            )
            choices.append(
                Choice(
                    "M-Masters",
                    "/bow/{}/?filter=M-Masters&phase={}".format(bow_slug, phase_choice),
                )
            )

    for k in categories:
        if phase_choice == "Final Results":
            choices.append(Choice(k.name, "/bow/{}/?filter={}".format(bow_slug, k.name)))
        else:
            choices.append(
                Choice(
                    k.name,
                    "/bow/{}/?filter={}&phase={}".format(bow_slug, k.name, phase_choice),
                )
            )
    choices = [x for x in choices if x.name != filter_choice]
    resultfilter = Filter(filter_choice, choices)
    return resultfilter


def getphasefilter(phase_choice, filter_choice, events_results_count, bow_slug):
    choices = []
    if phase_choice == "Final Results":
        loopcount = 1
        for count in events_results_count:
            if count == 0:
                phase_choice = "after-event-{}".format(loopcount - 1)
                break
            loopcount += 1
    if set(events_results_count) == {0}:
        phase_choice = False
    else:
        loopcount = 1
        for count in events_results_count:
            if count > 0:
                if loopcount == len(events_results_count):
                    if phase_choice != "Final Results":
                        if filter_choice == "":
                            choices.append(Choice("Final Results", "/bow/{}/".format(bow_slug)))
                        else:
                            choices.append(
                                Choice(
                                    "Final Results",
                                    "/bow/{}/?filter={}".format(bow_slug, filter_choice),
                                )
                            )
                else:
                    if phase_choice != "after-event-{}".format(loopcount):
                        if filter_choice == "":
                            choices.append(
                                Choice(
                                    "After Event {}".format(loopcount),
                                    "/bow/{}/?phase=after-event-{}".format(bow_slug, loopcount),
                                )
                            )
                        else:
                            choices.append(
                                Choice(
                                    "After Event {}".format(loopcount),
                                    "/bow/{}/?filter={}&phase=after-event-{}".format(
                                        bow_slug, filter_choice, loopcount
                                    ),
                                )
                            )
                    else:
                        phase_choice = "After Event {}".format(loopcount)
            loopcount += 1
    phasefilter = Filter(phase_choice, choices)
    return phasefilter
