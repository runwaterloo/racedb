from operator import attrgetter
from urllib import parse

from django.http import Http404
from django.shortcuts import render

from racedbapp.shared.types import Choice, Filter

from .models import Event, Result, Series


def index(request, series_slug):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    year = False
    all_series = Series.objects.filter(slug=series_slug).order_by("-year")
    if not all_series:
        raise Http404("Series not found")
    show_records = all_series.reverse()[0].show_records
    years = [x.year for x in all_series]
    if "year" in qstring:
        year = int(qstring["year"][0])
        all_series = all_series.filter(year=year)
    category = "All"
    if "filter" in qstring:
        category = qstring["filter"][0]
    all_series = [SeriesOccurence(x) for x in all_series]
    results = []
    for series in all_series:
        series_results = []
        event_ids = [x.id for x in series.events]

        # Create initial list of athletes from first event
        event1_all_results = Result.objects.filter(event_id=event_ids[0])
        event1_results = event1_all_results

        # Create list of filtered athletes
        for result in event1_results:
            series_results.append(SeriesResult(result, series.year))

        # Populate times for additional events
        for event in event_ids[1:]:
            event_dict = dict(
                Result.objects.filter(event_id=event).values_list("athlete", "guntime")
            )
            prev_results = series_results.copy()
            series_results = []
            if event_dict:  # if the event has results...
                for result in prev_results:
                    event_time = event_dict.get(result.athlete, None)
                    if event_time:
                        result.times.append(event_time)
                        result.total_time += event_time
                        series_results.append(result)
            elif year:  # if event has no results, but the URL has a year...
                for result in prev_results:
                    result.times.append(False)
                    series_results.append(result)
        results += series_results
    filters = {
        "category_filter": get_category_filter(
            series_slug, category, year, event1_all_results, results
        ),
        "year_filter": get_year_filter(series_slug, year, years, show_records),
    }
    # Apply filters
    if category in ("Female", "Male", "Masters", "F-Masters", "M-Masters"):
        if category in ("Female", "F-Masters"):
            results = [x for x in results if x.gender == "F"]
        if category in ("Male", "M-Masters"):
            results = [x for x in results if x.gender == "M"]
        if category in ("Masters", "F-Masters", "M-Masters"):
            results = [x for x in results if x.ismaster]
    elif category != "All":
        results = [x for x in results if x.category.name == category]

    # send results to template
    context = {
        "all_series": all_series,
        "filters": filters,
        "results": sorted(results, key=attrgetter("total_time")),
        "year": year,
    }
    return render(request, "racedbapp/series.html", context)


def get_year_filter(series_slug, year, years, show_records):
    choices = []
    for y in years:
        if y == year:
            continue
        choices.append(Choice(y, "/series/{}/?year={}".format(series_slug, y)))
    choices = sorted(choices, reverse=True)
    if year and show_records:
        current_choice = year
        choices.insert(0, Choice("All", "/series/{}/".format(series_slug)))
    else:
        current_choice = "All"
    year_filter = Filter(current_choice, choices)
    return year_filter


# TODO refactor with event version and have both call same.
def get_category_filter(series_slug, category, year, event1_all_results, results):
    choices = []
    if category == "All":
        current_choice = "All"
    else:
        current_choice = category
    event_categories = []
    if year:
        event_categories = (
            event1_all_results.exclude(category__name="")
            .values("category__name")
            .order_by("category__name")
            .distinct()
        ).values_list("category__name", flat=True)
    results_categories = [x.category.name for x in results]
    event_categories = [x for x in event_categories if x in results_categories]
    all_categories = ["Female", "Male", "Masters", "F-Masters", "M-Masters"] + list(
        event_categories
    )
    for cat in all_categories:
        if category != cat:
            if year:
                choices.append(
                    Choice(
                        cat,
                        "/series/{}/?year={}&filter={}".format(series_slug, year, cat),
                    )
                )
            else:
                choices.append(Choice(cat, "/series/{}/?filter={}".format(series_slug, cat)))
    if category != "All":
        if year:
            choices.insert(0, Choice("All", "/series/{}/?year={}".format(series_slug, year)))
        else:
            choices.insert(0, Choice("All", "/series/{}/".format(series_slug)))
    category_filter = Filter(current_choice, choices)
    return category_filter


class SeriesOccurence:
    def __init__(self, series):
        self.year = series.year
        self.name = series.name
        self.events = Event.objects.filter(id__in=series.event_ids.split(",")).order_by("date")

    def __repr__(self):
        return "SeriesOccurence(year={}, name={}, events={})".format(
            self.year, self.name, list(self.events)
        )


class SeriesResult:
    def __init__(self, result, year):
        self.year = year
        self.athlete = result.athlete
        if result.rwmember:
            self.member_slug = result.rwmember.slug
        else:
            self.member_slug = False
        self.gender = result.gender
        self.category = result.category
        self.ismaster = set_ismaster_from_result(result)
        self.times = [
            result.guntime,
        ]
        self.total_time = result.guntime

    def __repr__(self):
        return "SeriesResult(year={}, athlete={}, member={}, gender={}, category={}, total_time={}, times={})".format(
            self.year,
            self.athlete,
            self.member_slug,
            self.gender,
            self.category,
            self.total_time,
            [str(x) for x in self.times],
        )


def set_ismaster_from_result(result):
    ismaster = False
    if hasattr(result, "age") and result.age is not None:
        if result.age >= 40:
            ismaster = True
    elif hasattr(result, "category") and result.category is not None:
        if result.category.ismasters:
            ismaster = True
    return ismaster
