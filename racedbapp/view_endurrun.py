import os
import urllib
from collections import namedtuple
from datetime import timedelta
from operator import attrgetter

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils.html import conditional_escape
from django.utils.text import slugify

import racedbapp.shared.endurrun
from racedbapp.shared.tracing import tracer
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
    with tracer.start_as_current_span("endurrun: events query") as events_span:
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
    events_span.set_attribute("division", str(division))
    events_span.set_attribute("year", str(year))
    events_span.set_attribute("contest", str(contest_slug))
    events_span.set_attribute("years", len(years))
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
    with tracer.start_as_current_span("endurrun: year results") as year_results_span:
        year_results_span.set_attribute("division", str(division))
        year_results_span.set_attribute("years", len(years))
        year_bibs = {}
        # One pass over events (1 query) to group event ids by year, and one
        # bulk query for all results of those events. The old code issued 3
        # queries per event per year (COUNT + athlete/guntime + bib on the
        # first event), ~340 SELECTs total.
        division_suffix = None
        if division == "ultimate":
            division_suffix = "Ultimate"
        elif division == "sport":
            division_suffix = "Sport"
        event_year_map = list(events.values_list("id", "date__year"))
        year_event_ids = {}
        for event_id, event_year in event_year_map:
            year_event_ids.setdefault(event_year, []).append(event_id)
        event_rows = {}
        if year_event_ids:
            all_ids = [i for ids in year_event_ids.values() for i in ids]
            rows_q = Result.objects.filter(event_id__in=all_ids)
            if division_suffix:
                rows_q = rows_q.filter(division=division_suffix)
            for event_id, athlete, guntime, bib in rows_q.values_list(
                "event_id", "athlete", "guntime", "bib"
            ):
                event_rows.setdefault(event_id, []).append((athlete, guntime, bib))
        for loopyear in years:
            with tracer.start_as_current_span("endurrun: year results") as loop_span:
                loop_span.set_attribute("year", loopyear)
                if year:
                    if loopyear != year:
                        continue
                year_bibs[loopyear] = {}
                events_results_count = []
                all_event_results = []
                first_event = True
                for event_id in year_event_ids.get(loopyear, []):
                    rows = event_rows.get(event_id, [])
                    events_results_count.append(len(rows))
                    event_dict = {r[0]: r[1] for r in rows}
                    if first_event:
                        year_bibs[loopyear] = {r[0]: r[2] for r in rows}
                        first_event = False
                    all_event_results.append(event_dict)
                year_events_results_dict[loopyear] = all_event_results
                loop_span.set_attribute("events", len(all_event_results))
                loop_span.set_attribute("results", sum(events_results_count))
    if len(events_results_count) > 7:
        events_results_count = events_results_count[0:7]
    if not year:
        if division in ("ultimate", "relay"):
            events_results_count = (1, 1, 1, 1, 1, 1, 1)
        if division == "sport":
            events_results_count = (1, 1, 1)
    membership = shared.get_membership()
    with tracer.start_as_current_span("endurrun: athlete loop") as athlete_span:
        athlete_span.set_attribute("division", str(division))
        athlete_span.set_attribute("athletes", len(athletes))
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
    with tracer.start_as_current_span("endurrun: rank and gaps") as rank_span:
        rank_span.set_attribute("results", len(results))
        results = sorted(results, key=attrgetter("total_seconds"))
        results = sorted(results, key=attrgetter("stages"), reverse=True)
        results = addgap(results)
        results_ranked_athletes = [x.athlete for x in results]
        prev_stage_results = sorted(prev_stage_results, key=attrgetter("total_seconds"))
        prev_stage_results = sorted(prev_stage_results, key=attrgetter("stages"), reverse=True)
        prev_stage_ranked_athletes = [x.athlete for x in prev_stage_results]
        results = addchange(results, results_ranked_athletes, prev_stage_ranked_athletes)
    if results and not year and phase_choice == "Final Results":
        ultimate_gp = racedbapp.shared.endurrun.get_ultimate_gp(years)
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
    row_flags = {
        "division": division,
        "year": year,
        "contest_slug": contest_slug,
        "maxstages": maxstages,
        "phase_final": phasefilter.current == "Final Results",
        "ultimate_winners": ultimate_winners or set(),
        "ultimate_gold_jerseys": ultimate_gold_jerseys or set(),
    }
    # NOTE: unorthodox — the results table is built as one HTML string in
    # Python and dropped into endurrun.html with |safe, instead of being
    # rendered by the template (same pattern as the event view). Rationale:
    # the DTL row loop dominated cold renders (~1.2s of template lookups for
    # 676 rows); building rows in Python with conditional_escape cut that
    # dramatically. ALL result data passes through conditional_escape/_e in
    # _build_endurrun_row_html, so the |safe substitution is safe as long as
    # every value added there is escaped. The 9 golden endurrun pages
    # (rrw-notes/endurrun-golden-urls) guard this output byte-for-byte. If
    # you add a cell, add it in _build_endurrun_row_html AND a golden check.
    with tracer.start_as_current_span("endurrun: render table (python)") as table_span:
        table_span.set_attribute("results", len(results or []))
        results_table = _build_endurrun_table_html(results, row_flags)
    with tracer.start_as_current_span("endurrun: render") as render_span:
        render_span.set_attribute("results", len(results or []))
        render_span.set_attribute("years", len(years or []))
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
            "results_table": results_table,
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
    # rank lookup dicts (pk -> first position): list.index() on model
    # instances is O(n) per call with expensive __eq__, O(n^2) overall
    cur_rank = {}
    for i, a in enumerate(results_ranked_athletes):
        cur_rank.setdefault(a.pk, i)
    prev_rank = {}
    for i, a in enumerate(prev_stage_ranked_athletes):
        prev_rank.setdefault(a.pk, i)
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
            change = prev_rank[r.athlete.pk] - cur_rank[r.athlete.pk]
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



def _e(v):
    """HTML-escape a value; empty string for False/None."""
    return conditional_escape(v) if v else ""


_STAGE_SLUGS = {
    1: "half-marathon",
    2: "15-km",
    3: "30-km",
    4: "10-mi",
    5: "25_6-km",
    6: "10-km",
    7: "marathon",
}
_HEADER_STAGE_COLS = {
    "sprint": [2, 6],
    "trail": [3, 5],
    "sport": [5, 6, 7],
}


def _build_endurrun_table_html(results, f):
    """Assemble the endurrun results table (thead + tbody) as one HTML string.

    Mirrors the results-table markup in endurrun.html; row values are
    escaped here. See the NOTE in index() for the rationale and rules.
    """
    division = f["division"]
    year = f["year"]
    show_change = bool(year) and results and results[0].stages >= 2
    first_total_time = bool(results and results[0].total_time)
    show_camera = bool(year) and year >= 2014 and division != "relay" and first_total_time
    show_year_col = not year
    show_g = division != "relay"
    show_gp = show_g and show_year_col and f["phase_final"]
    show_total = first_total_time
    if division == "sport":
        header_stage_cols = _HEADER_STAGE_COLS["sport"]
    elif f.get("contest_slug") == "sprint":
        header_stage_cols = _HEADER_STAGE_COLS["sprint"]
    elif f.get("contest_slug") == "trail":
        header_stage_cols = _HEADER_STAGE_COLS["trail"]
    else:
        header_stage_cols = [1, 2, 3, 4, 5, 6, 7]

    head = ['  <table class="table table-striped table-hover table-condensed">', "  <thead>", "  <tr>"]
    if show_change:
        head.append(
            '    <th class="text-center"><i class="fa-regular fa-arrow-up-arrow-down" '
            'title="Place change since previous Stage"></i></th>'
        )
    head.append('    <th class="text-center">Place</th>')
    head.append("    <th>Name</th>")
    if show_camera:
        head.append(
            '    <th class="text-center" scope="col">\n        <i class="fas fa-camera"></i>\n'
            "    </th>"
        )
    if show_year_col:
        head.append('    <th class="text-center">Year</th>')
    if show_g:
        head.append('    <th class="text-center" title="Gender">G</th>')
        if show_gp:
            head.append('    <th class="text-center" title="Gender place for that year">GP</th>')
        head.append('    <th class="text-center">Age</th>')
    if show_total:
        head.append('    <th class="text-center">Total</th>')
        head.append('    <th class="text-center" title="Time gap to 1st place">Gap 1</th>')
        head.append('    <th class="text-center" title="Time gap to the next place up">Gap 2</th>')
        for c in header_stage_cols:
            head.append(f'    <th class="text-center">Stage {c}</th>')
    head.append("  </tr>")
    head.append("  </thead>")
    head.append("  <tbody>")

    rows = []
    for i, r in enumerate(results or []):
        rows.append(_build_endurrun_row_html(i + 1, r, f, show_change, show_camera, show_year_col, show_g, show_gp, show_total))
    return "\n".join(head) + "\n" + "\n".join(rows) + "\n  </tbody>\n</table>"


def _build_endurrun_row_html(
    place, r, f, show_change, show_camera, show_year_col, show_g, show_gp, show_total
):
    division = f["division"]
    year = f["year"]
    maxstages = f["maxstages"]
    cells = []
    if show_change:
        change = r.change
        if change > 0:
            cells.append(
                '      <td class="text-center">\n'
                '        <i class="fa-solid fa-chevron-up fa-lg" style="color:green"></i> '
                f"{_e(change)}\n      </td>"
            )
        elif change < 0:
            cells.append(
                '      <td class="text-center">\n'
                '        <i class="fa-solid fa-chevron-down fa-lg" style="color:red"></i> '
                f"{_e(change * -1)}\n      </td>"
            )
        else:
            cells.append('      <td class="text-center">\n      </td>')
    if r.final_status == 0:
        if r.stages == maxstages:
            cells.append(f'      <td class="text-center">{place}</td>')
        else:
            cells.append("      <td class=\"text-center\"></td>   <!-- Not started or in progress -->")
    else:
        if r.stages == maxstages:
            cells.append(f'      <td class="text-center">{place}</td>')
        elif r.final_status == 1:
            cells.append('      <td class="text-center">DQ</td>')
        else:
            cells.append('      <td class="text-center">DNF</td>')
    if r.mouseover:
        cells.append(f'      <td title="{_e(r.mouseover)}">')
    else:
        cells.append("      <td>")
    if r.flag_slug:
        cells.append(
            f'      <img title="{_e(r.athlete.country)}" '
            f'src="{settings.STATIC_URL}flags/{_e(r.flag_slug)}_shiny_24px.png">'
        )
    if r.athlete.name in f["ultimate_winners"]:
        cells.append(
            '      <i class="fa-solid fa-shirt-running fa-icon-ultimate-gold-jersey" '
            'title="Past ENDURrun Ultimate Champion"></i>'
        )
    elif r.athlete.name in f["ultimate_gold_jerseys"]:
        cells.append(
            '      <i class="fa-solid fa-shirt-tank-top fa-icon-ultimate-gold-jersey"  '
            'title="Gold Jersey Club member"></i>'
        )
    if r.member_slug:
        cells.append(f'        <a href="/member/{_e(r.member_slug)}/">{_e(r.athlete.name)}</a>')
    else:
        cells.append(f"        {_e(r.athlete.name)}")
    cells.append("      </td>")
    if show_camera:
        cells.append(
            '      <td class="text-center">\n'
            f'      <a href="https://www.flickr.com/photos/runwaterloo/tags/{year}endurrun,{_e(r.bib)}" '
            'target="_blank">\n        <i class="fas fa-camera"></i>      </a>\n    </td>'
        )
    if show_year_col:
        cells.append(f'      <td class="text-center">{_e(r.athlete.year)}</td>')
    if show_g:
        cells.append(f'      <td class="text-center">{_e(r.athlete.gender)}</td>')
        if show_gp:
            if r.gp:
                cells.append(f'      <td class="text-center">{_e(r.gp)}</td>')
            else:
                cells.append("      <td></td>")
        if r.athlete.age:
            cells.append(f'      <td class="text-center">{_e(r.athlete.age)}</td>')
        else:
            cells.append("      <td></td>")
    if show_total:
        cells.append(f'      <td class="text-center">{_e(r.total_time)}</td>')
        cells.append(f'      <td class="text-center">{_e(r.lead_gap)}</td>')
        cells.append(f'      <td class="text-center">{_e(r.place_gap)}</td>')
        if not r.stage_times:
            # quirk from the original template: </tr> only renders inside the
            # stage_times else-branch, so these rows have no closing tag
            return "    <tr>\n" + "\n".join(cells) + "\n      <td></td><td></td><td></td><td></td><td></td><td></td><td></td>"
        else:
            for counter, t in enumerate(r.stage_times, start=1):
                title = f' title="{_e(t.name)}"' if division == "relay" else ""
                if counter <= 4 and division != "sport":
                    cells.append(
                        f'      <td class="text-center"{title}><a href="/event/{_e(r.athlete.year)}/'
                        f'endurrun/{_STAGE_SLUGS[counter]}/?division={division.title()}">{_e(t.time)}</a></td>'
                    )
                if counter == 5:
                    cells.append(
                        f'      <td class="text-center"{title}><a href="/event/{_e(r.athlete.year)}/'
                        f'endurrun/{_STAGE_SLUGS[5]}/?division={division.title()}">{_e(t.time)}</a></td>'
                    )
                elif counter == 6:
                    cells.append(
                        f'      <td class="text-center"{title}><a href="/event/{_e(r.athlete.year)}/'
                        f'endurrun/{_STAGE_SLUGS[6]}/?division={division.title()}">{_e(t.time)}</a></td>'
                    )
                elif counter == 7:
                    cells.append(
                        f'      <td class="text-center"{title}><a href="/event/{_e(r.athlete.year)}/'
                        f'endurrun/{_STAGE_SLUGS[7]}/?division={division.title()}">{_e(t.time)}</a></td>'
                    )
    return "    <tr>\n" + "\n".join(cells) + "\n    </tr>"
