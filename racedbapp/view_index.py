import urllib

# from django.db.models import Min, Q
# from django import db
from collections import namedtuple
from datetime import datetime
from operator import attrgetter
from types import SimpleNamespace

from django.db.models import Count
from django.shortcuts import render

from . import config, view_endurrun, view_event, view_member, view_recap
from .models import Config, Endurraceresult, Event, Relay, Result, Rwmember
from .shared import cache_lock, shared, utils

EventContext = namedtuple("EventContext", ["date", "city"], defaults=(None, None))
RaceContext = namedtuple("RaceContext", ["name", "shortname", "slug"], defaults=(None, None, None))
DistanceContext = namedtuple("DistanceContext", ["name", "slug", "km"], defaults=(None, None, None))
MemberInfoContext = namedtuple(
    "MemberInfoContext",
    ["member", "racing_since", "km", "fivek_pb", "tenk_pb"],
    defaults=(None, None, None, None, None),
)
RecapContext = namedtuple(
    "RecapContext",
    ["results", "event", "type", "distances", "race_logo_slug", "series"],
    defaults=(None, None, None, None, None, None),
)
FeaturedEventContext = namedtuple(
    "FeaturedEventContext",
    ["event", "data", "future_events", "race_logo_slug"],
    defaults=(None, None, None),
)


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    if "asofdate" in qstring:
        return _render_index(request)
    # Only asofdate affects the rendered page; any other query params are
    # ignored so arbitrary junk params can't fragment the cache (PR #444).
    return cache_lock.get_or_render("index", lambda: _render_index(request))


def _render_index(request):
    """Render the full index page (expensive; only called on cache miss)."""
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    asofdate = None
    if "asofdate" in qstring:
        asofdate = qstring["asofdate"][0]
    recap_context = get_recap_context(asofdate)
    member_info_context = get_memberinfo()
    featured_event_context = get_featured_event_context()
    notification = get_notification()
    context = {
        "distances": recap_context.distances,
        "recap_type": recap_context.type,
        "recap_event": recap_context.event,
        "recap_race_logo_slug": recap_context.race_logo_slug,
        "recap_results": recap_context.results,
        "recap_series": recap_context.series,
        "memberinfo": member_info_context,
        "featured_event": featured_event_context.event,
        "featured_race_logo_slug": featured_event_context.race_logo_slug,
        "featured_event_data": featured_event_context.data,
        "future_events": featured_event_context.future_events,
        "notification": notification,
    }
    html = render(request, "racedbapp/index.html", context)
    return html


def get_recap_context(asofdate):
    allResults = Result.objects.all()
    if not allResults.exists():
        return RecapContext()
    last_race_day_events = get_last_race_day_events(allResults, asofdate)
    recap_type = get_recap_type(last_race_day_events)
    distances = get_distances(last_race_day_events)
    recap_event = get_recap_event(last_race_day_events, recap_type, distances)
    race_logo_slug = utils.get_race_logo_slug(recap_event.race.slug)
    recap_results = get_recap_results(recap_event, recap_type)
    recap_series = view_event.get_series(events=last_race_day_events)
    return RecapContext(
        recap_results, recap_event, recap_type, distances, race_logo_slug, recap_series
    )


def get_last_race_day_events(allResults, asofdate):
    if not allResults.exists():
        return
    if asofdate:
        maxdate = datetime.strptime(asofdate, "%Y-%m-%d")
        date_of_last_event = (
            allResults.filter(event__date__lte=maxdate).order_by("-event__date")[:1][0].event.date
        )
    else:
        date_of_last_event = allResults.order_by("-event__date")[:1][0].event.date
    last_race = (
        allResults.filter(event__date=date_of_last_event).order_by("-event__date")[:1][0].event.race
    )
    last_race_day_event_ids = (
        Result.objects.filter(event__race=last_race, event__date__year=date_of_last_event.year)
        .values_list("event", flat=True)
        .distinct()
    )
    last_race_day_events = Event.objects.filter(id__in=last_race_day_event_ids).order_by(
        "-date", "-distance__km"
    )
    return last_race_day_events


def get_recap_results(recap_event, recap_type):
    if recap_type == "relay":
        recap_results = get_recap_results_relay(recap_event)
    elif recap_type == "combined":
        recap_results = get_recap_results_combined(recap_event)
    elif recap_type == "endurrun":
        recap_results = get_recap_results_endurrun(recap_event)
    else:
        recap_results = get_recap_results_standard(recap_event)
    return recap_results


def get_recap_results_relay(recap_event):
    # TODO calling other view functions and indices has code smell refactor
    relay_records = shared.get_relay_records(year=recap_event.date.year)
    categories = config.ValidRelayCategories().categories.values()
    recap_results = {}
    for i in categories:
        if relay_records[i]:
            fastest_times = relay_records[i]
            winner = sorted(fastest_times, key=attrgetter("team_place"))[0]
            recap_results[i] = winner
    return recap_results


def get_recap_results_combined(recap_event):
    request = {}
    year = recap_event.date.year
    race_slug = recap_event.race.slug
    distance_slug = "combined"
    recap_results = view_recap.index(request, year, race_slug, distance_slug, individual_only=True)
    return recap_results


def get_recap_results_endurrun(recap_event):
    recap_results = Endurrunrecap(recap_event)
    return recap_results


def get_recap_results_standard(recap_event):
    event_results = Result.objects.filter(event=recap_event)
    hasmasters = Result.objects.hasmasters(recap_event)
    distance_slug = recap_event.distance.slug
    recap_results = view_recap.get_individual_results(
        recap_event, event_results, hasmasters, distance_slug
    )
    return recap_results


def get_recap_event(last_race_day_events, recap_type, distances):
    """Choose which event to use for a recap"""
    distance_slugs = [x.slug for x in distances]
    if recap_type == "relay" and "2_5-km" in distance_slugs:
        recap_event = last_race_day_events.filter(distance__slug="2_5-km")[0]
    else:
        recap_event = last_race_day_events[0]
    return recap_event


def get_recap_type(last_race_day_events):
    if not last_race_day_events.exists():
        return
    recap_type = "standard"
    if last_race_day_events[0].race.slug == "laurier-loop":
        relay_event = [x for x in last_race_day_events if x.distance.slug == "2_5-km"]
        if len(relay_event) == 1:
            if Relay.objects.filter(event=relay_event[0]).count() > 0:
                recap_type = "relay"
    if last_race_day_events[0].race.slug == "endurrace":
        year = last_race_day_events[0].date.year
        if Endurraceresult.objects.filter(year=year).count() > 0:
            recap_type = "combined"
    if last_race_day_events[0].race.slug == "endurrun":
        recap_type = "endurrun"
    return recap_type


def get_distances(last_race_day_events):
    if not last_race_day_events.exists():
        return
    distances = []
    for e in last_race_day_events:
        distance = shared.set_distance_display_name(e.distance, e.sequel)
        distances.append(distance)
    return distances


def get_memberinfo():
    members = (
        Rwmember.objects.filter(active=True)
        .exclude(photourl=None)
        .exclude(photourl="")
        .order_by("?")
    )
    if not members.exists():
        return MemberInfoContext()
    featured_member_id = "0"
    db_featured_member_id = Config.objects.filter(name="featured_member_id")
    if db_featured_member_id.count() > 0:
        featured_member_id = db_featured_member_id[0].value
    if featured_member_id.isdigit():
        featured_member_id = int(featured_member_id)
    valid_member_ids = [x.id for x in members]
    if featured_member_id in valid_member_ids:
        member = [x for x in members if x.id == featured_member_id][0]
        member_results, km = view_member.get_memberresults(member)
    else:
        for member in members:
            member_results, km = view_member.get_memberresults(member)
            if km > 0:
                break
    km = round(km, 1)
    racing_since = ""
    fivek_pb = view_member.get_pb(member_results, "5-km")
    tenk_pb = view_member.get_pb(member_results, "10-km")
    if len(member_results) > 0:
        racing_since = member_results[-1].result.event.date.year
    MemberInfoContext(member, racing_since, km, fivek_pb, tenk_pb)
    return MemberInfoContext(member, racing_since, km, fivek_pb, tenk_pb)


def get_featured_event_context():
    events = Event.objects.all()
    if not events.exists():
        return FeaturedEventContext()
    event = get_featured_event()
    race_logo_slug = ""
    if event:
        race_logo_slug = utils.get_race_logo_slug(event.race.slug)
    return FeaturedEventContext(
        event, get_event_data(event), get_future_events(event), race_logo_slug
    )


def get_featured_event():
    featured_event = None
    try:
        featured_event_id = int(Config.objects.get(name="homepage_featured_event_id").value)
    except Exception:
        pass
    else:
        try:
            event = Event.objects.get(id=featured_event_id)
        except Exception:
            pass
        else:
            finishers = Result.objects.filter(event=event).count()
            if finishers == 0:
                featured_event = event
    return featured_event


def get_event_records(race, distance):
    """All-time overall + masters records for a race/distance, one query.

    Purpose-built for the upcoming-events table: returns the same
    namedresult rows the table consumes from
    shared.get_race_records(individual_only=True), computed in a single
    pass over one query instead of ~10 category scans with tie-breaker
    re-queries.
    """
    races = shared.create_samerace_list(race)
    membership = shared.get_membership()
    # Lightweight tuples, not ORM objects: this scans a race's full
    # all-time history, so model instantiation for every row dominates
    # cold-render CPU. Pull only the columns the records need.
    raw = (
        Result.objects.filter(
            event__race__in=races,
            event__distance=distance,
            gender__in=("M", "F"),
        )
        .exclude(guntime=None)
        .values_list(
            "guntime",
            "athlete",
            "age",
            "city",
            "place",
            "gender",
            "category__ismasters",
            "category__name",
            "event_id",
            "event__date",
            "event__race__slug",
        )
    )
    is_endurrun = race.slug == "endurrun"
    best = {}  # demographic -> [time, row tuples]
    for t, athlete, age, city, place, gender, ismasters, cat_name, event_id, event_date, race_slug in raw:
        if is_endurrun:
            is_master = age is not None and age >= 40
        else:
            is_master = ismasters or (age is not None and age >= 40)
        demos = [gender]
        if is_master:
            demos.append("Masters Male" if gender == "M" else "Masters Female")
        for demo in demos:
            current = best.get(demo)
            if current is None or t < current[0]:
                best[demo] = [t, [(t, athlete, age, city, place, cat_name, event_id, event_date, race_slug)]]
            elif t == current[0]:
                current[1].append((t, athlete, age, city, place, cat_name, event_id, event_date, race_slug))
    demo_order = ["M", "F", "Masters Male", "Masters Female"]
    records = []
    for demo in demo_order:
        if demo not in best:
            continue
        t, tied = best[demo]
        label = "Overall Male" if demo == "M" else "Overall Female"
        if demo.startswith("Masters"):
            label = demo
        for t, athlete, age, city, place, cat_name, event_id, event_date, race_slug in sorted(
            tied, key=lambda x: x[7]
        ):
            fake = SimpleNamespace(
                athlete=athlete,
                place=place,
                event=SimpleNamespace(id=event_id),
            )
            records.append(
                shared.namedresult(
                    label,
                    t,
                    athlete,
                    event_date.year,
                    cat_name,
                    city,
                    age,
                    race_slug,
                    shared.get_member(fake, membership),
                )
            )
    return records


def get_event_data(event):
    if not event:
        return None
    previous_event = (
        Event.objects.filter(race=event.race, distance=event.distance)
        .exclude(id=event.id)
        .order_by("-date")
        .first()
    )
    if previous_event is None:
        return None
    previous_event_recap = get_recap_results_standard(previous_event)
    featured_event_records = get_event_records(event.race, event.distance)
    event_data = []
    for i in featured_event_records:
        row = UpcomingEvent()
        row.event = event
        row.previous_event = previous_event
        row.previous_event_year = previous_event.date.year
        row.demographic = i.place
        row.record_athlete = i.athlete
        row.record_member = i.member
        row.record_time = i.guntime
        row.record_year = i.year
        recap_row = 0
        if "Master" in row.demographic:
            recap_row = 3
        if "Female" in row.demographic:
            row.last_year_winning_athlete = previous_event_recap[recap_row].female_athlete
            row.last_year_winning_member = previous_event_recap[recap_row].female_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].female_time
        else:
            row.last_year_winning_athlete = previous_event_recap[recap_row].male_athlete
            row.last_year_winning_member = previous_event_recap[recap_row].male_member_slug
            row.last_year_winning_time = previous_event_recap[recap_row].male_time
        event_data.append(row)
    return event_data


def get_future_events(event):
    """Return all upcoming events of the next N races, in date order.

    Two-phase to keep the query count flat: phase 1 walks the (single)
    future-events query in Python to find the N races, using one batched
    per-event result count; phase 2 builds the display list from the same
    in-memory rows, using one batched per-(race, distance) result count.
    Per-event get_event_data runs only for events that will display.
    """
    today = datetime.today()
    dbfuture_events = list(
        Event.objects.filter(date__gte=today)
        .select_related("race", "distance")
        .order_by("date", "-distance__km")
    )
    if not dbfuture_events:
        return []
    upcoming_races_count_object = Config.objects.filter(
        name="homepage_upcoming_races_count"
    ).first()
    upcoming_races_count = (
        int(upcoming_races_count_object.value) if upcoming_races_count_object else 5
    )

    exclude_events_objects = Config.objects.filter(
        name="homepage_upcoming_exclude_events"
    ).first()
    exclude_events_str = exclude_events_objects.value.split(",") if exclude_events_objects else []
    exclude_events = [int(x) for x in exclude_events_str]

    # One grouped count instead of one count() per event.
    result_counts = dict(
        Result.objects.filter(event_id__in=[i.id for i in dbfuture_events])
        .values_list("event_id")
        .annotate(n=Count("id"))
    )

    # Phase 1: find the first N races, preserving the original semantics:
    # a race counts as seen only via an event that is not excluded, not the
    # featured event, and has no results yet.
    races_seen = []
    races_seen_ids = set()
    for i in dbfuture_events:
        if i.id in exclude_events or i == event:
            continue
        if result_counts.get(i.id, 0) > 0:
            continue
        if i.race_id not in races_seen_ids:
            if len(races_seen) == upcoming_races_count:
                break
            races_seen.append(i.race)
            races_seen_ids.add(i.race_id)

    # Phase 2: all no-result events of the chosen races, in original order.
    # History check is a per-event exists() probe (indexed, early-exit,
    # <1ms each, at most one per displayed event) instead of one
    # all-time grouped count over every race's full result history.
    future_events = []
    for i in dbfuture_events:
        if i.race_id not in races_seen_ids:
            continue
        if i.id in exclude_events or i == event or result_counts.get(i.id, 0) > 0:
            continue
        numresults = Result.objects.filter(
            event__race_id=i.race_id, event__distance_id=i.distance_id
        ).exists()
        event_data = get_event_data(i) if numresults else False
        race_logo_slug = utils.get_race_logo_slug(i.race.slug)
        future_events.append((i, event_data, race_logo_slug))
    return future_events


def get_notification():
    notification = False
    notifications = Config.objects.filter(name="homepage_notification")
    if len(notifications) == 1:
        dbvalue = notifications[0].value
        if dbvalue != "":
            notification = dbvalue
    return notification


class UpcomingEvent:
    def __init__(self):
        self.demographic = None
        self.last_year_winning_athlete = None
        self.last_year_winning_member_slug = None
        self.last_year_winning_time = None
        self.record_athlete = None
        self.record_time = None
        self.record_year = None


class Endurrunrecap:
    def __init__(self, event):
        self.year = event.date.year
        self.distance_slug = event.distance.slug
        self.endurrun_stages = {
            "half-marathon": 1,
            "15-km": 2,
            "30-km": 3,
            "10-mi": 4,
            "25_6-km": 5,
            "10-km": 6,
            "marathon": 7,
        }
        self.stage_number = self.endurrun_stages.get(self.distance_slug)
        self.ultimate_suffix = "after Stage {}".format(self.stage_number)
        if self.stage_number == 7:
            self.ultimate_suffix += " (Final)"
        self.top_female = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("Female",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0:3]
        self.top_male = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("Male",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0:3]
        self.top_f_masters = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("F-Masters",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0]
        self.top_m_masters = view_endurrun.index(
            {
                "year": (str(self.year),),
                "filter": ("M-Masters",),
                "phase": ("after-stage-{}".format(str(self.stage_number)),),
            },
            "ultimate",
            results_only=True,
        )[0]

    def __str__(self):
        return "year={}, ultimate_suffix={}".format(self.year, self.ultimate_suffix)
