import os
import urllib
from collections import namedtuple
from datetime import timedelta
from operator import attrgetter

from django.http import Http404
from django.shortcuts import render
from django.utils.text import slugify

import racedbapp.shared.endurrun
from racedbapp.shared.types import Choice, Filter

from .models import Endurathlete, Endurteam, Event, Result
from .shared import shared

namedstagetime = namedtuple("ns", ["name", "time"])
namedresult = namedtuple(
    "na",
    [
        "athlete",
        "stages",
        "total_time",
        "total_seconds",
        "stage_times",
        "flag_slug",
        "final_status",
        "mouseover",
        "lead_gap",
        "place_gap",
        "member_slug",
        "bib",
        "change",
        "gp",
    ],
)


def index(request, division, results_only=False):
    if results_only:
        qstring = request
    else:
        qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    year = False
    if "year" in qstring:
        rawyear = qstring["year"][0]
        if rawyear.isdigit():
            year = int(rawyear)
        else:
            raise Http404('Year "{}" not found'.format(rawyear))
    years = Endurathlete.objects.all().order_by("-year").values_list("year", flat=True).distinct()
    contest_slug = False
    if "contest" in qstring:
        contest_slug = qstring["contest"][0]
        if year:
            ultimate_finished_all_events = (
                racedbapp.shared.endurrun.get_ultimate_finished_all_events((year,))
            )
        else:
            ultimate_finished_all_events = (
                racedbapp.shared.endurrun.get_ultimate_finished_all_events(years)
            )
    events = Event.objects.filter(race__slug="endurrun").order_by("date")
    if division == "sport":
        events = events.exclude(distance__slug="half-marathon")
        events = events.exclude(distance__slug="15-km")
        events = events.exclude(distance__slug="30-km")
        events = events.exclude(distance__slug="10-mi")
    if contest_slug == "sprint":
        events = events.exclude(distance__slug="half-marathon")
        events = events.exclude(distance__slug="30-km")
        events = events.exclude(distance__slug="10-mi")
        events = events.exclude(distance__slug="25_6-km")
        events = events.exclude(distance__slug="marathon")
    if contest_slug == "trail":
        events = events.exclude(distance__slug="half-marathon")
        events = events.exclude(distance__slug="15-km")
        events = events.exclude(distance__slug="10-mi")
        events = events.exclude(distance__slug="10-km")
        events = events.exclude(distance__slug="marathon")
    if division in ("ultimate", "sport"):
        athletes = Endurathlete.objects.filter(division=division.title()).order_by("id")
    else:
        athletes = Endurteam.objects.all()
    if year:
        events = events.filter(date__icontains=year)
        athletes = athletes.filter(year=year)
    filter_choice = ""
    if "filter" in qstring:
        filter_choice = qstring["filter"][0]
    stop_event = 999999
    phase_choice = "Final Results"
    if "phase" in qstring:
        phase_choice = qstring["phase"][0]
        stop_event = int(phase_choice.split("-")[2])
        if division == "sport":
            stop_event = stop_event - 4
    results = []
    prev_stage_results = []
    if division in ("ultimate", "sport"):
        if filter_choice == "Female":
            athletes = athletes.filter(gender="F")
        elif filter_choice == "Male":
            athletes = athletes.filter(gender="M")
        elif filter_choice == "Masters":
            athletes = athletes.filter(age__gte=40)
        elif filter_choice == "F-Masters":
            athletes = athletes.filter(gender="F", age__gte=40)
        elif filter_choice == "M-Masters":
            athletes = athletes.filter(gender="M", age__gte=40)
    elif division == "relay":
        if filter_choice == "Female":
            athletes = athletes.filter(gender="F")
        elif filter_choice == "Male":
            athletes = athletes.filter(gender="M")
        elif filter_choice == "Mixed":
            athletes = athletes.filter(gender="X")
        elif filter_choice == "Masters":
            athletes = athletes.filter(ismasters=True)
    hasmasters = True
    year_events_results_dict = {}
    events_results_count = []
    flags = os.listdir("/srv/racedb/racedbapp/static/flags")
    valid_flag_slugs = {x.split("_")[0] for x in flags}
    year_bibs = {}
    for loopyear in years:
        if year:
            if loopyear != year:
                continue
        year_bibs[loopyear] = {}
        events_results_count = []
        all_event_results = []
        for event in events.filter(date__icontains=loopyear):
            event_results = Result.objects.filter(event=event)
            if division == "ultimate":
                event_results = event_results.filter(division="Ultimate")
            if division == "sport":
                event_results = event_results.filter(division="Sport")
            events_results_count.append(event_results.count())
            event_dict = dict(event_results.values_list("athlete", "guntime"))
            if not year_bibs[loopyear]:
                year_bibs[loopyear] = dict(event_results.values_list("athlete", "bib"))
            all_event_results.append(event_dict)
        year_events_results_dict[loopyear] = all_event_results
    if len(events_results_count) > 7:
        events_results_count = events_results_count[0:7]
    if not year:
        if division in ("ultimate", "relay"):
            events_results_count = (1, 1, 1, 1, 1, 1, 1)
        if division == "sport":
            events_results_count = (1, 1, 1)
    membership = shared.get_membership()
    for athlete in athletes:
        if contest_slug:  # exclude athletes who haven't completed most recent event
            if not ultimate_finished_all_events[athlete.year].get(athlete, False):
                continue
        final_status = 0  # 0: place, 1: dq, 2: dnf, 3: dns
        mouseover = False
        if division == "relay":
            mouseover = "{}\n".format(athlete.name)
        athyear = athlete.year
        stages = 0
        stage_times = []
        total_time = timedelta(seconds=0)
        count = 1
        member_slug = False
        if athlete.name.lower() in membership.names:
            member_slug = membership.names[athlete.name.lower()].slug
        for er in year_events_results_dict[athyear]:
            try:
                if division in ("ultimate", "sport"):
                    athname = athlete.name
                else:
                    evalstr = "athlete.st{}".format(count)
                    athname = eval(evalstr)
                    if athname == "":
                        athname = False
                    mouseover += "\nStage {}: {}".format(count, athname)
                stage_time = namedstagetime(athname, er[athname])
            except Exception:
                stage_time = namedstagetime("", "")
            else:
                if count <= stop_event and stage_time.time.days == 0:
                    stages += 1
                    total_time += stage_time.time
                else:
                    if 356400 <= stage_time.time.total_seconds() < 357000:
                        stage_time = namedstagetime(athname, "DQ")
                        final_status = 1
                    elif 357000 <= stage_time.time.total_seconds() < 357600:
                        stage_time = namedstagetime(athname, "DNF")
                        final_status = 2
                    elif stage_time.time.total_seconds() >= 357600:
                        stage_time = namedstagetime(athname, "DNS")
                        final_status = 3
                if count > stop_event:
                    stage_time = namedstagetime("", "")
            stage_times.append(stage_time)
            count += 1
        if division == "sport":
            stage_times = [
                namedstagetime("", ""),
                namedstagetime("", ""),
                namedstagetime("", ""),
                namedstagetime("", ""),
            ] + stage_times
        if total_time == timedelta(seconds=0):
            total_seconds = 0
        else:
            total_seconds = total_time.total_seconds()
        if total_time.total_seconds() > 86400:
            strtime = str(total_time)
            days = strtime.split(" ")[0]
            hours, minutes, seconds = strtime.split(" ")[2].split(":")
            total_hours = int(hours) + (24 * int(days))
            total_time = "{}:{}:{}".format(total_hours, minutes, seconds)
        if total_seconds == 0:
            total_time = ""
        flag_slug = False
        if division in ("ultimate", "sport"):
            flag_slug = slugify(athlete.country)
            if flag_slug not in valid_flag_slugs:
                flag_slug = False
        lead_gap = place_gap = False
        bib = year_bibs[athyear].get(athname)
        results.append(
            namedresult(
                athlete,
                stages,
                total_time,
                total_seconds,
                stage_times,
                flag_slug,
                final_status,
                mouseover,
                lead_gap,
                place_gap,
                member_slug,
                bib,
                "",
                "",
            )
        )
        prev_total_time = total_time
        prev_total_seconds = total_seconds
        prev_stages = stages
        completed_stage_times = [x for x in stage_times if x.name != ""]  # remove future stages
        if completed_stage_times and year:
            if not isinstance(
                completed_stage_times[-1].time, str
            ):  # ensure most recent stage completed
                try:
                    prev_total_time = total_time - completed_stage_times[-1].time
                except Exception:
                    prev_total_time = timedelta(seconds=0)
                prev_total_seconds = prev_total_time.total_seconds()
                prev_stages = stages - 1
        prev_stage_results.append(
            namedresult(
                athlete,
                prev_stages,
                prev_total_time,
                prev_total_seconds,
                # placeholder data from here on
                [],
                "",
                0,
                "",
                0,
                0,
                "",
                "",
                "",
                "",
            )
        )
    results = sorted(results, key=attrgetter("total_seconds"))
    results = sorted(results, key=attrgetter("stages"), reverse=True)
    results = addgap(results)
    results_ranked_athletes = [x.athlete for x in results]
    prev_stage_results = sorted(prev_stage_results, key=attrgetter("total_seconds"))
    prev_stage_results = sorted(prev_stage_results, key=attrgetter("stages"), reverse=True)
    prev_stage_ranked_athletes = [x.athlete for x in prev_stage_results]
    results = addchange(results, results_ranked_athletes, prev_stage_ranked_athletes)
    if results and not year and phase_choice == "Final Results":
        ultimate_gp = racedbapp.shared.endurrun.get_ultimate_gp()
        results = addgp(results, ultimate_gp)
    maxstages = 0
    if results and len(results) > 0:
        maxstages = results[0].stages
    if results_only:
        return results
    divisionfilter = getdivisionfilter(division, year, contest_slug)
    resultfilter = getresultfilter(
        filter_choice, phase_choice, division, hasmasters, year, contest_slug
    )
    phasefilter = getphasefilter(phase_choice, filter_choice, events_results_count, division, year)
    athletes = [x.athlete.name for x in results] if results else None
    (
        ultimate_winners,
        ultimate_gold_jerseys,
    ) = racedbapp.shared.endurrun.get_ultimate_winners_and_gold_jerseys(years, athletes)
    context = {
        "events": events,
        "events_results_count": events_results_count,
        "divisionfilter": divisionfilter,
        "resultfilter": resultfilter,
        "phasefilter": phasefilter,
        "year": year,
        "years": years,
        "division": division,
        "maxstages": maxstages,
        "results": results,
        "contest_slug": contest_slug,
        "ultimate_winners": ultimate_winners,
        "ultimate_gold_jerseys": ultimate_gold_jerseys,
    }
    return render(request, "racedbapp/endurrun.html", context)


def getdivisionfilter(division, year, contest_slug):
    if contest_slug:
        filter_choice = "Ultimate-{}".format(contest_slug.title())
    else:
        filter_choice = division.title()
    append_list = []
    sprint_append_list = []
    trail_append_list = []
    if year:
        append_list.append("year={}".format(year))
        sprint_append_list.append("year={}".format(year))
        trail_append_list.append("year={}".format(year))
    sprint_append_list.append("contest=sprint")
    trail_append_list.append("contest=trail")
    append_string = ""
    if append_list:
        append_string = "?" + "&".join(sorted(append_list))
    sprint_append_string = "?" + "&".join(sorted(sprint_append_list))
    trail_append_string = "?" + "&".join(sorted(trail_append_list))
    choices = [
        Choice("Ultimate", "/endurrun/ultimate/{}".format(append_string)),
        Choice("Relay", "/endurrun/relay/{}".format(append_string)),
        Choice("Ultimate-Sprint", "/endurrun/ultimate/{}".format(sprint_append_string)),
        Choice("Ultimate-Trail", "/endurrun/ultimate/{}".format(trail_append_string)),
        Choice("Sport", "/endurrun/sport/{}".format(append_string)),
    ]
    choices = [x for x in choices if x.name != filter_choice]
    divisionfilter = Filter(filter_choice, choices)
    return divisionfilter


def getresultfilter(filter_choice, phase_choice, division, hasmasters, year, contest_slug):
    contest_qs1 = contest_qs2 = ""
    if contest_slug:
        contest_qs1 = "?contest={}".format(contest_slug)
        contest_qs2 = "&contest={}".format(contest_slug)
    if year:
        if phase_choice == "Final Results":
            choices = [
                Choice("", "/endurrun/{}/?year={}{}".format(division, year, contest_qs2)),
                Choice(
                    "Female",
                    "/endurrun/{}/?year={}&filter=Female{}".format(division, year, contest_qs2),
                ),
                Choice(
                    "Male",
                    "/endurrun/{}/?year={}&filter=Male{}".format(division, year, contest_qs2),
                ),
            ]
            if division == "relay":
                choices.append(
                    Choice(
                        "Mixed",
                        "/endurrun/{}/?year={}&filter=Mixed".format(division, year),
                    )
                )
            if hasmasters:
                choices.append(
                    Choice(
                        "Masters",
                        "/endurrun/{}/?year={}&filter=Masters{}".format(
                            division, year, contest_qs2
                        ),
                    )
                )
                choices.append(
                    Choice(
                        "F-Masters",
                        "/endurrun/{}/?year={}&filter=F-Masters{}".format(
                            division, year, contest_qs2
                        ),
                    )
                )
                choices.append(
                    Choice(
                        "M-Masters",
                        "/endurrun/{}/?year={}&filter=M-Masters{}".format(
                            division, year, contest_qs2
                        ),
                    )
                )
        else:
            choices = [
                Choice(
                    "",
                    "/endurrun/{}/?year={}&phase={}".format(division, year, phase_choice),
                ),
                Choice(
                    "Female",
                    "/endurrun/{}/?year={}&filter=Female&phase={}".format(
                        division, year, phase_choice
                    ),
                ),
                Choice(
                    "Male",
                    "/endurrun/{}/?year={}&filter=Male&phase={}".format(
                        division, year, phase_choice
                    ),
                ),
            ]
            if division == "relay":
                choices.append(
                    Choice(
                        "Mixed",
                        "/endurrun/{}/?year={}&filter=Mixed&phase={}".format(
                            division, year, phase_choice
                        ),
                    )
                )
            if hasmasters:
                choices.append(
                    Choice(
                        "Masters",
                        "/endurrun/{}/?year={}&filter=Masters&phase={}".format(
                            division, year, phase_choice
                        ),
                    )
                )
                choices.append(
                    Choice(
                        "F-Masters",
                        "/endurrun/{}/?year={}&filter=F-Masters&phase={}".format(
                            division, year, phase_choice
                        ),
                    )
                )
                choices.append(
                    Choice(
                        "M-Masters",
                        "/endurrun/{}/?year={}&filter=M-Masters&phase={}".format(
                            division, year, phase_choice
                        ),
                    )
                )
    else:
        if phase_choice == "Final Results":
            choices = [
                Choice("", "/endurrun/{}/{}".format(division, contest_qs1)),
                Choice(
                    "Female",
                    "/endurrun/{}/?filter=Female{}".format(division, contest_qs2),
                ),
                Choice("Male", "/endurrun/{}/?filter=Male{}".format(division, contest_qs2)),
            ]
            if division == "relay":
                choices.append(Choice("Mixed", "/endurrun/{}/?filter=Mixed".format(division)))
            if hasmasters:
                choices.append(
                    Choice(
                        "Masters",
                        "/endurrun/{}/?filter=Masters{}".format(division, contest_qs2),
                    )
                )
                choices.append(
                    Choice(
                        "F-Masters",
                        "/endurrun/{}/?filter=F-Masters{}".format(division, contest_qs2),
                    )
                )
                choices.append(
                    Choice(
                        "M-Masters",
                        "/endurrun/{}/?filter=M-Masters{}".format(division, contest_qs2),
                    )
                )
        else:
            choices = [
                Choice("", "/endurrun/{}/?phase={}".format(division, phase_choice)),
                Choice(
                    "Female",
                    "/endurrun/{}/?filter=Female&phase={}".format(division, phase_choice),
                ),
                Choice(
                    "Male",
                    "/endurrun/{}/?filter=Male&phase={}".format(division, phase_choice),
                ),
            ]
            if division == "relay":
                choices.append(
                    Choice(
                        "Mixed",
                        "/endurrun/{}/?filter=Mixed&phase={}".format(division, phase_choice),
                    )
                )
            if hasmasters:
                choices.append(
                    Choice(
                        "Masters",
                        "/endurrun/{}/?filter=Masters&phase={}".format(division, phase_choice),
                    )
                )
                choices.append(
                    Choice(
                        "F-Masters",
                        "/endurrun/{}/?filter=F-Masters&phase={}".format(division, phase_choice),
                    )
                )
                choices.append(
                    Choice(
                        "M-Masters",
                        "/endurrun/{}/?filter=M-Masters&phase={}".format(division, phase_choice),
                    )
                )
    choices = [x for x in choices if x.name != filter_choice]
    if division == "relay":  # omit filters that Jordan doesn't want
        choices = [x for x in choices if x.name != "M-Masters"]
        choices = [x for x in choices if x.name != "F-Masters"]
    resultfilter = Filter(filter_choice, choices)
    return resultfilter


def getphasefilter(phase_choice, filter_choice, events_results_count, division, year):
    choices = []
    if phase_choice == "Final Results":
        loopcount = 1
        if division == "sport":
            loopcount = 5
        for count in events_results_count:
            if count == 0:
                phase_choice = "after-stage-{}".format(loopcount - 1)
                break
            loopcount += 1
    if set(events_results_count) == {0}:
        phase_choice = False
    else:
        loopcount = 1
        offset = 0
        if division == "sport":
            loopcount = 5
            offset = 4
        for count in events_results_count:
            if count > 0:
                if year:
                    if loopcount - offset == len(events_results_count):
                        if phase_choice != "Final Results":
                            if filter_choice == "":
                                choices.append(
                                    Choice(
                                        "Final Results",
                                        "/endurrun/{}/?year={}".format(division, year),
                                    )
                                )
                            else:
                                choices.append(
                                    Choice(
                                        "Final Results",
                                        "/endurrun/{}/?year={}&filter={}".format(
                                            division, year, filter_choice
                                        ),
                                    )
                                )
                    else:
                        if phase_choice != "after-stage-{}".format(loopcount):
                            if filter_choice == "":
                                choices.append(
                                    Choice(
                                        "After Stage {}".format(loopcount),
                                        "/endurrun/{}/?year={}&phase=after-stage-{}".format(
                                            division, year, loopcount
                                        ),
                                    )
                                )
                            else:
                                choices.append(
                                    Choice(
                                        "After Stage {}".format(loopcount),
                                        "/endurrun/{}/?year={}&filter={}&phase=after-stage-{}".format(
                                            division, year, filter_choice, loopcount
                                        ),
                                    )
                                )
                        else:
                            phase_choice = "After Stage {}".format(loopcount)
                else:
                    if loopcount - offset == len(events_results_count):
                        if phase_choice != "Final Results":
                            if filter_choice == "":
                                choices.append(
                                    Choice(
                                        "Final Results",
                                        "/endurrun/{}/".format(division),
                                    )
                                )
                            else:
                                choices.append(
                                    Choice(
                                        "Final Results",
                                        "/endurrun/{}/?filter={}".format(division, filter_choice),
                                    )
                                )
                    else:
                        if phase_choice != "after-stage-{}".format(loopcount):
                            if filter_choice == "":
                                choices.append(
                                    Choice(
                                        "After Stage {}".format(loopcount),
                                        "/endurrun/{}/?phase=after-stage-{}".format(
                                            division, loopcount
                                        ),
                                    )
                                )
                            else:
                                choices.append(
                                    Choice(
                                        "After Stage {}".format(loopcount),
                                        "/endurrun/{}/?filter={}&phase=after-stage-{}".format(
                                            division, filter_choice, loopcount
                                        ),
                                    )
                                )
                        else:
                            phase_choice = "After Stage {}".format(loopcount)
            loopcount += 1
    phasefilter = Filter(phase_choice, choices)
    return phasefilter


def addgap(results):
    """Calculate time gap between places and add them"""
    newresults = []
    previous_seconds = False
    if len(results) > 0:
        stages = results[0].stages
        lead_seconds = results[0].total_seconds
    for r in results:
        lead_gap = place_gap = ""
        if r.stages == stages and r.total_time != "" and r.total_seconds != lead_seconds:
            lead_gapseconds = r.total_seconds - lead_seconds
            lead_gap = timedelta(seconds=lead_gapseconds)
            if previous_seconds:
                place_gapseconds = r.total_seconds - previous_seconds
                place_gap = timedelta(seconds=place_gapseconds)
        previous_seconds = r.total_seconds
        newresults.append(
            namedresult(
                r.athlete,
                r.stages,
                r.total_time,
                r.total_seconds,
                r.stage_times,
                r.flag_slug,
                r.final_status,
                r.mouseover,
                lead_gap,
                place_gap,
                r.member_slug,
                r.bib,
                "",
                "",
            )
        )
    return newresults


def addchange(results, results_ranked_athletes, prev_stage_ranked_athletes):
    """Calculate rank change"""
    newresults = []
    if not results:
        return None
    if results[0].stages < 2:
        change = False
        for r in results:
            newresults.append(
                namedresult(
                    r.athlete,
                    r.stages,
                    r.total_time,
                    r.total_seconds,
                    r.stage_times,
                    r.flag_slug,
                    r.final_status,
                    r.mouseover,
                    r.lead_gap,
                    r.place_gap,
                    r.member_slug,
                    r.bib,
                    change,
                    "",
                )
            )
    else:
        for r in results:
            change = prev_stage_ranked_athletes.index(r.athlete) - results_ranked_athletes.index(
                r.athlete
            )
            newresults.append(
                namedresult(
                    r.athlete,
                    r.stages,
                    r.total_time,
                    r.total_seconds,
                    r.stage_times,
                    r.flag_slug,
                    r.final_status,
                    r.mouseover,
                    r.lead_gap,
                    r.place_gap,
                    r.member_slug,
                    r.bib,
                    change,
                    "",
                )
            )
    return newresults


def addgp(results, ultimate_gp):
    """Calculate gender place"""
    newresults = []
    for r in results:
        gp = False
        if r.athlete.year in ultimate_gp:
            gp = ultimate_gp[r.athlete.year].get(r.athlete.name, False)
        newresults.append(
            namedresult(
                r.athlete,
                r.stages,
                r.total_time,
                r.total_seconds,
                r.stage_times,
                r.flag_slug,
                r.final_status,
                r.mouseover,
                r.lead_gap,
                r.place_gap,
                r.member_slug,
                r.bib,
                r.change,
                gp,
            )
        )
    return newresults
