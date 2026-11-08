from collections import OrderedDict, defaultdict
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from operator import attrgetter
from urllib import parse

from django.db.models import Count, Exists, OuterRef
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.html import escape

from racedbapp.shared import cache_lock
from racedbapp.shared.tracing import tracer
from racedbapp.shared.types import Choice, Filter

from .models import Config, Event, Result, Rwmember, Rwmembertag


def index(request, year, leaderboard_only=False, standings_only=False):
    with tracer.start_as_current_span("boost: boost years"):
        boost_years = get_boost_years()
    if not boost_years:
        return render(request, "racedbapp/boost.html")
    if year == "latest":
        return redirect("/boost/{}/".format(boost_years[0]))
    else:
        year = int(year)
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    qs_filter = get_qs_filter(qstring)
    qs_date = get_qs_date(qstring, year)
    # Expensive computation (config, gender finishers, previous races,
    # dbresults, standings) is cached per (year, qs_date) and shared by the
    # boost and member views. Request-specific bits (qs_filter, qs_member)
    # are applied afterwards in Python, uncached. Invalidated by
    # cache_lock.bump_generation like all generation-stamped entries.
    compute = cache_lock.get_or_render(
        "boost.compute.{}.{}".format(year, qs_date or "all"),
        lambda: _compute_boost(year, qs_date),
    )
    if standings_only:
        return compute["standings"]
    if leaderboard_only:
        return compute["leaderboard"]
    qs_member = False
    member_results = None
    # Member matching runs after the early returns so leaderboard_only /
    # standings_only callers are never exposed to ?member= errors.
    if "member" in qstring:
        with tracer.start_as_current_span("boost: qs member"):
            included_members = Rwmember.objects.filter(
                year_of_birth__isnull=False,
                tags=compute["boost_tag"],
                gender__in=["M", "F"],
            )
            qs_member = get_qs_member(qstring, included_members)
        if qs_member:
            member_results = next(
                (i for i in compute["standings"] if i.member_id == qs_member.id), None
            )
            if member_results is None:
                raise Http404("No boost results for member")
    standings = [
        (i, row)
        for i, row in zip(compute["standings"], compute["standings_rows"])
        if _matches_qs_filter(i, qs_filter)
    ]
    # Filtered views renumber rows (the template used forloop.counter over
    # the filtered list), so stamp the prebuilt placeholder per position.
    standings_rows = [
        row.replace("@@PLACE@@", str(n)) for n, (i, row) in enumerate(standings, 1)
    ]
    standings = [i for i, row in standings]

    def render_boost_page():
        if qs_member:
            context = {
                "config_dict": compute["config_dict"],
                "qs_member": qs_member,
                "member_results": member_results,
                "year": year,
            }
            with tracer.start_as_current_span("boost: render template"):
                return render(request, "racedbapp/boost_member.html", context)
        with tracer.start_as_current_span("boost: render filters"):
            standings_filter = get_standings_filter(qs_filter, qs_date, year)
            date_filter = get_date_filter(qs_date, year)
        context = {
            "leaderboard_html": compute["leaderboard_html"],
            "standings_rows": "\n".join(standings_rows),
            "standings_filter": standings_filter,
            "date_filter": date_filter,
            "qs_date": qs_date,
            "year": year,
            "boost_years": boost_years,
        }
        with tracer.start_as_current_span("boost: render template"):
            return render(request, "racedbapp/boost.html", context)

    if not qs_filter and not qs_date and not qs_member:
        # Bare /boost/<year>/ is the hottest URL: cache the full render too.
        return cache_lock.get_or_render(
            "boost.render.{}".format(year), render_boost_page
        )
    return render_boost_page()


def get_qs_date(qstring, year):
    qs_date = ""
    if "date" in qstring:
        try:
            ymd = [int(x) for x in qstring["date"][0].split("-")]
            qs_date = datetime(*ymd).date()
        except Exception:
            raise Http404("Invalid date")
        else:
            first_day = datetime(year, 1, 1).date()
            last_day = datetime(year, 12, 31).date()
            if not first_day <= qs_date <= last_day:
                raise Http404("Invalid date")
    return qs_date


def _matches_qs_filter(i, qs_filter):
    """Filter one standing entry by the ?filter= querystring value."""
    if qs_filter == "":
        return True
    if qs_filter in ("F", "M"):
        return i.gender == qs_filter
    return i.category == qs_filter


def _compute_boost(year, qs_date):
    """Compute boost standings for (year, qs_date). Cached as one unit.

    Returns the request-independent pieces: the full unfiltered standings
    list (with places assigned), the leaderboard, the boost tag, and the
    config dict. Querystring filtering and member matching happen outside.
    """
    config_values = (
        "boost_classic_points",
        "boost_ditto_points",
        "boost_leaderboard_size",
        "boost_max_endurrun",
        "boost_max_events",
        "boost_max_sport",
        "boost_merit_max",
        "boost_participation_points",
        "boost_pb_points",
        "nophoto_url",
    )
    with tracer.start_as_current_span("boost: config"):
        config_dict = dict(Config.objects.values_list("name", "value").filter(name__in=config_values))
    max_events = int(config_dict.get("boost_max_events", 0))
    max_endurrun = int(config_dict.get("boost_max_endurrun", 0))
    max_sport = int(config_dict.get("boost_max_sport", 0))
    leaderboard_size = int(config_dict.get("boost_leaderboard_size", 0))
    nophoto_url = config_dict.get("nophoto_url", "")
    first_day = datetime(year, 1, 1).date()
    last_day = datetime(year, 12, 31).date()
    if qs_date:
        last_day = qs_date
    with tracer.start_as_current_span("boost: gender finishers"):
        gender_finishers = get_gender_finishers(first_day, last_day)
    with tracer.start_as_current_span("boost: boost tag"):
        boost_tag = get_boost_tag(year)
    with tracer.start_as_current_span("boost: included members"):
        included_members = Rwmember.objects.filter(
            year_of_birth__isnull=False,
            tags=boost_tag,
            gender__in=["M", "F"],
        )
    with tracer.start_as_current_span("boost: previous races"):
        previous_races = get_previous_races(year, included_members)
    battlers = {}
    with tracer.start_as_current_span("boost: battlers"):
        for i in included_members:
            battlers[i.id] = Battler(i, year, nophoto_url)
    dbresults = (
        Result.objects.select_related(
            "event__race", "event__distance", "event__sequel"
        )
        .values(
            "rwmember_id",
            "gender",
            "guntime",
            "gender_place",
            "isrwpb",
            "event__id",
            "event__race_id",
            "event__race__shortname",
            "event__race__slug",
            "event__distance__name",
            "event__distance__slug",
            "event__sequel__name",
            "event__sequel__slug",
        )
        .filter(
            event__date__range=(first_day, last_day),
            gender_place__isnull=False,
            rwmember__in=included_members,
        )
        .order_by("event__date")
    )
    with tracer.start_as_current_span("boost: results + bresults"):
        for i in dbresults:
            battlers[i["rwmember_id"]].results.append(
                BResult(i, gender_finishers, config_dict, previous_races)
            )
    with tracer.start_as_current_span("boost: calculate"):
        for v in battlers.values():
            v.calculate(max_events, max_endurrun, max_sport)
    gender_place_dict = {"F": 0, "M": 0, "NB": 0}
    category_place_dict = {}
    leaders = {"F40-": [], "M40-": [], "F40+": [], "M40+": [], "NB40-": [], "NB40+": []}
    standings = []
    count = 1
    with tracer.start_as_current_span("boost: standings"):
        for i in sorted(battlers.values(), key=attrgetter("total_points"), reverse=True):
            if i.total_points == 0:
                continue
            i.place = count
            count += 1
            if i.gender in gender_place_dict:
                gender_place_dict[i.gender] += 1
                i.gender_place = gender_place_dict[i.gender]
            if i.category in category_place_dict:
                category_place_dict[i.category] += 1
                i.category_place = category_place_dict[i.category]
            else:
                if i.gender in gender_place_dict:
                    i.category_place = category_place_dict[i.category] = 1
            if i.gender in gender_place_dict:
                if len(leaders[i.category]) < leaderboard_size:
                    leaders[i.category].append(i)
            standings.append(i)
    leaderboard = OrderedDict()
    leaderboard["Female Under 40"] = leaders["F40-"]
    leaderboard["Male Under 40"] = leaders["M40-"]
    leaderboard["Female Over 40"] = leaders["F40+"]
    leaderboard["Male Over 40"] = leaders["M40+"]
    with tracer.start_as_current_span("boost: prebuild html"):
        standings_rows, leaderboard_html = _prebuild_html(
            standings, leaderboard, qs_date
        )
    return {
        "config_dict": config_dict,
        "standings": standings,
        "standings_rows": standings_rows,
        "leaderboard": leaderboard,
        "leaderboard_html": leaderboard_html,
        "boost_tag": boost_tag,
    }


def _fmt_points(value, decimals):
    """Match Django's floatformat: ROUND_HALF_UP, fixed decimals."""
    q = Decimal(str(value)).quantize(
        Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP
    )
    text = "{v:f}".format(v=q)
    if decimals == 0:
        text = text.split(".")[0]
    return text


def _standings_row(i, qs_date):
    """One <tr> of the standings table as prebuilt HTML.

    The place number is a placeholder: filtered views renumber rows
    (forloop.counter over the filtered list), so the number is stamped in
    at request time. Everything else is request-independent.
    """
    points_fmt = _fmt_points(i.total_points, 0)
    points_title = _fmt_points(i.total_points, 2)
    athlete = escape(i.athlete)
    slug = escape(i.slug)
    city = escape(i.city)
    if qs_date == "":
        total_cell = (
            '<td class="text-center"><a href="?member={slug}" '
            'title="{title}">{points}<a></td>'.format(
                slug=slug, title=points_title, points=points_fmt
            )
        )
    else:
        total_cell = (
            '<td class="text-center" title="{title}">{points}</td>'.format(
                title=points_title, points=points_fmt
            )
        )
    if i.active:
        athlete_cell = '<a href="/member/{slug}/">{athlete}</a>'.format(
            slug=slug, athlete=athlete
        )
    else:
        athlete_cell = athlete
    return (
        '<tr><td class="text-center">@@PLACE@@</td>'
        + total_cell
        + "<td>"
        + athlete_cell
        + '</td><td class="text-center">'
        + escape(i.gender)
        + '</td><td class="text-center">'
        + str(i.gender_place)
        + "</td><td class=\"text-center\">"
        + escape(i.category)
        + '</td><td class="text-center">'
        + str(i.category_place)
        + "</td><td>"
        + city
        + "</td></tr>"
    )


def _leaderboard_row(i, qs_date):
    """One <tr> of a leaderboard mini-table as prebuilt HTML."""
    points_fmt = _fmt_points(i.total_points, 0)
    points_title = _fmt_points(i.total_points, 2)
    athlete = escape(i.athlete)
    slug = escape(i.slug)
    if qs_date == "":
        total_cell = (
            '<td><a href="?member={slug}" '
            'title="{title}">{points}<a></td>'.format(
                slug=slug, title=points_title, points=points_fmt
            )
        )
    else:
        total_cell = '<td title="{title}">{points}</td>'.format(
            title=points_title, points=points_fmt
        )
    if i.active:
        athlete_cell = '<a href="/member/{slug}/">{athlete}</a>'.format(
            slug=slug, athlete=athlete
        )
    else:
        athlete_cell = athlete
    return (
        "<tr><td class=\"text-center\">"
        + str(i.place)
        + "</td>"
        + total_cell
        + "<td>"
        + athlete_cell
        + "</td></tr>"
    )


def _prebuild_html(standings, leaderboard, qs_date):
    """Prebuild the standings rows and leaderboard tables as HTML strings.

    Moved out of the Django template so cold renders skip template CPU for
    the ~280-row standings table. Slicing for ?filter= happens in the view;
    rows carry a @@PLACE@@ placeholder that gets renumbered there.
    """
    standings_rows = [_standings_row(i, qs_date) for i in standings]
    leaderboard_html = OrderedDict()
    for k, v in leaderboard.items():
        leaderboard_html[k] = "\n".join(_leaderboard_row(i, qs_date) for i in v)
    return standings_rows, leaderboard_html


def get_boost_years():
    boost_tags = Rwmembertag.objects.values_list("name", flat=True).filter(name__icontains="boost-")
    boost_tag_years = [x.split("-")[1] for x in boost_tags]
    found_year_results = False
    boost_years = []
    for i in sorted(boost_tag_years, reverse=True):
        if i.isdigit():
            if found_year_results:
                boost_years.append(int(i))
            else:
                year_result_count = Result.objects.filter(event__date__icontains=i).count()
                if year_result_count > 0:
                    boost_years.append(int(i))
                    found_year_results = True
    return boost_years


def get_boost_tag(year):
    try:
        boost_tag = Rwmembertag.objects.get(name="boost-{}".format(year))
    except Exception:
        raise Http404("No results found")
    return boost_tag


def get_qs_filter(qstring):
    valid_filters = ("F", "M", "F40-", "F40+", "M40-", "M40+")
    qs_filter = ""
    if "filter" in qstring:
        raw_filter = qstring["filter"][0]
        if raw_filter in valid_filters:
            qs_filter = raw_filter
        else:
            raise Http404("Filter not found")
    return qs_filter


def get_standings_filter(qs_filter, qs_date, year):
    choices = []
    append_date = ""
    if qs_date != "":
        append_date = "?date={}".format(qs_date)
    choices.append(Choice("", "/boost/{}/{}".format(year, append_date)))
    if qs_date != "":
        append_date = "&date={}".format(qs_date)
    choices.append(Choice("Female", "/boost/{}/?filter=F{}".format(year, append_date)))
    choices.append(Choice("Male", "/boost/{}/?filter=M{}".format(year, append_date)))
    choices.append(Choice("F40-", "/boost/{}/?filter=F40-{}".format(year, append_date)))
    choices.append(Choice("M40-", "/boost/{}/?filter=M40-{}".format(year, append_date)))
    choices.append(Choice("F40+", "/boost/{}/?filter=F40+{}".format(year, append_date)))
    choices.append(Choice("M40+", "/boost/{}/?filter=M40+{}".format(year, append_date)))
    choices = [x for x in choices if x.name != qs_filter]
    if qs_filter == "F":
        current_choice = "Female"
    elif qs_filter == "M":
        current_choice = "Male"
    elif qs_filter == "":
        current_choice = ""
    else:
        current_choice = qs_filter
    standings_filter = Filter(current_choice, choices)
    return standings_filter


def get_date_filter(qs_date, year):
    current_choice = False
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    last_event_date = (
        Event.objects.filter(date__range=(start_date, end_date)).order_by("-date")[0].date
    )
    if (datetime.now().date() - last_event_date).days > 7:
        final = True
    else:
        final = False
    events = (
        Event.objects.select_related()
        .filter(date__range=(start_date, end_date))
        .filter(Exists(Result.objects.filter(event=OuterRef("pk"))))
        .order_by("-date")
    )
    if len(events) == 0:
        raise Http404("No events found")
    choices = []
    dates_seen = []
    racedates = defaultdict(list)
    for e in events:
        if e.date not in racedates[e.race]:
            racedates[e.race].append(e.date)
    for e in events:
        if e.date in dates_seen:
            continue
        if len(racedates[e.race]) > 1:
            choice = Choice(
                "{} {}".format(e.race.shortname, e.distance.name),
                "/boost/{}/?date={}".format(year, e.date),
            )
        else:
            choice = Choice(e.race.name, "/boost/{}/?date={}".format(year, e.date))
        if e.date != qs_date:
            choices.append(choice)
        else:
            current_choice = choice.name
        dates_seen.append(e.date)
    first_choice = choices[0].name
    if final:
        first_choice += " (Final)"
    else:
        first_choice += " (Current)"
    del choices[0]
    if current_choice:
        choices.insert(0, Choice(first_choice, "/boost/{}/".format(year)))
    if not current_choice:
        current_choice = first_choice
    date_filter = Filter(current_choice, choices)
    return date_filter


def get_previous_races(year, included_members):
    previous_year = year - 1
    first_day = datetime(previous_year, 1, 1).date()
    last_day = datetime(previous_year, 12, 31).date()
    previous_races = {}
    results = (
        Result.objects.order_by()
        .filter(
            event__date__range=(first_day, last_day), rwmember_id__in=included_members
        )
        .values_list("rwmember_id", "event__race_id")
    )
    for rwmember_id, race_id in results:
        if rwmember_id in previous_races:
            previous_races[rwmember_id].add(race_id)
        else:
            previous_races[rwmember_id] = {race_id}
    return previous_races


def get_gender_finishers(first_day, last_day):
    # Filter on event_id__in so Postgres drives from the (few) events in
    # range via the result.event_id FK index, instead of seq-scanning the
    # whole result table (issue #444).
    db = (
        Result.objects.filter(
            event_id__in=Event.objects.filter(
                date__range=(first_day, last_day)
            ).values("id"),
            gender__in=["F", "M"],
            place__lt=990000,
        )
        .values("event_id", "gender")
        .annotate(num_finishers=Count("id"))
    )
    gender_finishers = {"F": {}, "M": {}}
    for j in db:
        gender_finishers[j["gender"]][j["event_id"]] = j["num_finishers"]
    return gender_finishers


def get_qs_member(qstring, included_members):
    member = False
    if "member" in qstring:
        members = included_members.filter(slug=qstring["member"][0])
        if len(members) == 1:
            member = members[0]
        else:
            raise Http404("Member not found")
    return member


class Battler:
    def __init__(self, member, year, nophoto_url):
        self.member_id = member.id
        self.year = year
        self.active = member.active
        self.athlete = member.name
        self.slug = member.slug
        self.gender = member.gender
        self.age = year - member.year_of_birth
        if member.photourl:
            self.photourl = member.photourl
        else:
            self.photourl = nophoto_url
        self.ismaster = False
        self.category_suffix = "40-"
        if self.age >= 40:
            self.ismaster = True
            self.category_suffix = "40+"
        self.category = self.gender + self.category_suffix
        self.city = member.city
        self.results = []
        self.total_points = 0
        self.gender_place = 0
        self.category_place = 0

    def calculate(self, max_events, max_endurrun, max_sport):
        self.results = sorted(self.results, key=attrgetter("ep"), reverse=True)
        events_count = endurrun_count = sport_count = 0
        for i in self.results:
            if events_count == max_events:
                break
            else:
                if "endurrun" in i.event_race_slug:
                    if endurrun_count == max_endurrun:
                        continue
                    else:
                        endurrun_count += 1
                elif i.event_race_slug == "sport":
                    if sport_count == max_sport:
                        continue
                    else:
                        sport_count += 1
                events_count += 1
                i.counts = True
                self.total_points += i.ep
        self.results = sorted(self.results, key=attrgetter("counts", "ep"), reverse=True)


class BResult:
    def __init__(self, r, gender_finishers, config_dict, previous_races):
        """Built from a .values() dict (see _compute_boost), not model instances."""
        sequel_name = r["event__sequel__name"]
        if sequel_name:
            self.event_distance_name = sequel_name
            sequel_slug = r["event__sequel__slug"]
        else:
            self.event_distance_name = r["event__distance__name"]
            sequel_slug = None
        self.event_id = r["event__id"]
        self.event_race_short_name = r["event__race__shortname"]
        self.event_race_slug = r["event__race__slug"]
        self.event_distance_slug = r["event__distance__slug"]
        if sequel_slug:
            self.event_distance_slug += "/{}".format(sequel_slug)
        self.guntime = r["guntime"]
        self.gender_place = r["gender_place"]
        self.gender_finishers = gender_finishers[r["gender"]][r["event__id"]]
        self.mp = (1 - (self.gender_place / self.gender_finishers)) * int(
            config_dict["boost_merit_max"]
        )
        self.ditto_boost = self.pb_boost = self.classic_boost = 0
        if r["rwmember_id"] in previous_races:
            if r["event__race_id"] in previous_races[r["rwmember_id"]]:
                self.ditto_boost = int(config_dict["boost_ditto_points"])
        if r["isrwpb"]:
            self.pb_boost = int(config_dict["boost_pb_points"])
        if self.event_race_slug in ("waterloo-classic", "fall-classic"):
            self.classic_boost = int(config_dict["boost_classic_points"])
        self.ep = sum(
            [
                int(config_dict["boost_participation_points"]),
                self.mp,
                self.ditto_boost,
                self.pb_boost,
                self.classic_boost,
            ]
        )
        self.counts = False
