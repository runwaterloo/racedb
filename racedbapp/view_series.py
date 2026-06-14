from operator import attrgetter
from urllib import parse

from django.http import Http404
from django.shortcuts import render

from racedbapp.shared import agegrade
from racedbapp.shared.types import Choice, Filter

from .models import Event, Result, Series

AGE_GRADE_SCORING = "age-grade"


def index(request, series_slug):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    year = False
    all_series = Series.objects.filter(slug=series_slug).order_by("-year")
    if not all_series:
        raise Http404("Series not found")
    representative_series = all_series.reverse()[0]
    show_records = representative_series.show_records
    age_grade_enabled = representative_series.age_grade_enabled
    # Age-grade scoring is only honored when the series opts in via its flag.
    scoring = qstring.get("scoring", [None])[0]
    age_grade = age_grade_enabled and scoring == AGE_GRADE_SCORING
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
        event_ids = [x.id for x in series.events]
        # Kept for the category filter below (athlete categories from event one).
        event1_all_results = Result.objects.filter(event_id=event_ids[0])
        if age_grade:
            results += build_age_grade_results(series, year)
        else:
            results += build_total_time_results(series, event1_all_results, year)
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

    if age_grade:
        results = sorted(results, key=attrgetter("total_age_grade"), reverse=True)
    else:
        results = sorted(results, key=attrgetter("total_time"))

    # send results to template
    context = {
        "all_series": all_series,
        "filters": filters,
        "results": results,
        "year": year,
        "scoring": scoring if age_grade else None,
        "age_grade_enabled": age_grade_enabled,
        "scoring_toggle": (
            get_scoring_toggle(series_slug, year, category) if age_grade_enabled else None
        ),
    }
    return render(request, "racedbapp/series.html", context)


def get_scoring_toggle(series_slug, year, category):
    """Build Total Time / Age Grade toggle URLs that preserve year and filter."""
    base = "/series/{}/".format(series_slug)
    common = []
    if year:
        common.append(("year", year))
    if category and category != "All":
        common.append(("filter", category))

    def build(extra):
        params = common + extra
        if params:
            return base + "?" + "&".join("{}={}".format(k, v) for k, v in params)
        return base

    return {
        "total_time_url": build([]),
        "age_grade_url": build([("scoring", AGE_GRADE_SCORING)]),
    }


def build_total_time_results(series, event1_all_results, year):
    """Build the Total Time standings for one series occurrence."""
    series_results = []
    event_ids = [x.id for x in series.events]

    # Create initial list of athletes from first event
    for result in event1_all_results:
        series_results.append(SeriesResult(result, series.year))

    # Populate times for additional events
    for event in event_ids[1:]:
        event_dict = dict(Result.objects.filter(event_id=event).values_list("athlete", "guntime"))
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
    return series_results


def build_age_grade_results(series, year):
    """Build the age-grade standings for one series occurrence.

    Each event is graded by its own distance; the per-event grade is rounded to
    two decimals and these rounded values are summed (so the displayed columns
    add up). The every-event membership rule matches the Total Time path.
    """
    events = list(series.events)
    series_results = []

    # Seed from the first event.
    first_event = events[0]
    first_distance_m = float(first_event.distance.km) * 1000
    for result in Result.objects.filter(event_id=first_event.id):
        ag_result = SeriesAgeGradeResult(result, series.year)
        age = resolve_age(result.age, result.rwmember, first_event.date.year)
        grade = round(
            agegrade.age_grade(
                first_distance_m, result.gender, age, grading_seconds(result.guntime)
            ),
            2,
        )
        ag_result.times = [grade]
        ag_result.total_age_grade = grade
        series_results.append(ag_result)

    # Grade each additional event and keep only athletes present in all of them.
    for event in events[1:]:
        distance_m = float(event.distance.km) * 1000
        event_year = event.date.year
        event_dict = {
            athlete: (guntime, age, year_of_birth)
            for athlete, guntime, age, year_of_birth in Result.objects.filter(
                event_id=event.id
            ).values_list("athlete", "guntime", "age", "rwmember__year_of_birth")
        }
        prev_results = series_results.copy()
        series_results = []
        if event_dict:  # if the event has results...
            for ag_result in prev_results:
                event_row = event_dict.get(ag_result.athlete)
                if event_row and event_row[0]:  # guntime present
                    guntime, result_age, year_of_birth = event_row
                    age = resolve_age_from_year(result_age, year_of_birth, event_year)
                    grade = round(
                        agegrade.age_grade(
                            distance_m, ag_result.gender, age, grading_seconds(guntime)
                        ),
                        2,
                    )
                    ag_result.times.append(grade)
                    ag_result.total_age_grade += grade
                    series_results.append(ag_result)
        elif year:  # if event has no results, but the URL has a year...
            for ag_result in prev_results:
                ag_result.times.append(False)
                series_results.append(ag_result)
    return series_results


def grading_seconds(guntime):
    """Finish time (seconds) used for age grading.

    Single, isolated read point for the grading time source. Swap ``guntime``
    for ``chiptime`` here to change the source for the whole age-grade view.
    """
    return guntime.total_seconds()


def resolve_age(result_age, rwmember, event_year):
    """Age cascade for a full ``Result`` object (the seed event)."""
    year_of_birth = rwmember.year_of_birth if rwmember else None
    return resolve_age_from_year(result_age, year_of_birth, event_year)


def resolve_age_from_year(result_age, year_of_birth, event_year):
    """Resolve age: ``Result.age`` → event year − year_of_birth → ``None``."""
    if result_age is not None:
        return result_age
    if year_of_birth:
        return event_year - year_of_birth
    return None


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


class SeriesAgeGradeResult:
    """A standings row in age-grade mode.

    Mirrors ``SeriesResult`` for the shared columns (year, athlete, gender,
    category, ismaster) but tracks per-event age grades and their summed total.
    ``times`` and ``total_age_grade`` are populated by ``build_age_grade_results``.
    """

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
        self.times = []
        self.total_age_grade = 0

    def __repr__(self):
        return (
            "SeriesAgeGradeResult(year={}, athlete={}, gender={}, category={}, "
            "total_age_grade={}, times={})".format(
                self.year,
                self.athlete,
                self.gender,
                self.category,
                self.total_age_grade,
                self.times,
            )
        )


def set_ismaster_from_result(result):
    ismaster = False
    if result.age:
        if result.age >= 40:
            ismaster = True
        else:
            ismaster = False
    elif result.category.ismasters:
        ismaster = True
    return ismaster
