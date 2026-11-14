import logging
from collections import defaultdict, namedtuple
from operator import attrgetter
from urllib import parse

from django.db.models import (
    BooleanField,
    Count,
    Exists,
    F,
    Min,
    OuterRef,
    Q,
    Value,
)
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.html import conditional_escape

from racedbapp.shared.types import Choice, Filter
from racedbapp.tasks import safe_enqueue, send_email_task

from .models import (
    Config,
    Durelay,
    Endurteam,
    Event,
    Phototag,
    Prime,
    Relay,
    Result,
    Sequel,
    Series,
    Split,
    Wheelchairresult,
)
from .shared import cache_lock, shared, utils
from .shared.tracing import tracer
from .templatetags.racedbapp_extras import get_pace, get_place, round_up, show_str_decimal

logger = logging.getLogger(__name__)

named_split = namedtuple("ns", ["split_num", "split_time"])
# Lightweight stand-in passed to shared.get_member(): the row loop reads
# results as plain dicts (model instantiation is too expensive at scale),
# but get_member() expects .athlete / .event.id attribute access.
_MemberKey = namedtuple("_MemberKey", ["athlete", "event", "place"])


def get_series(event=None, events=None, year=None, race=None):
    series = []
    all_series = Series.objects.all().order_by("year")
    event_ids = {current_event.id for current_event in events} if events is not None else set()
    for current_series in all_series:
        series_event_ids = [
            int(x.strip()) for x in current_series.event_ids.split(",") if x.strip().isdigit()
        ]
        if event is not None and event.id in series_event_ids:
            series.append(current_series)
        elif events is not None and event_ids.intersection(series_event_ids):
            series.append(current_series)
        elif event is None and year is not None and race is not None:
            if Event.objects.filter(
                id__in=series_event_ids, date__year=year, race_id=race.id
            ).exists():
                series.append(current_series)
    return series


def _get_event_cache_days():
    """Days in the past an event stays cacheable. 0 disables; default 60."""
    value = shared.get_config_value_or_false("event_cache_days")
    if not value:
        return 60
    try:
        return int(value)
    except (TypeError, ValueError):
        return 60


def _is_cacheable(event, request):
    days = _get_event_cache_days()
    if days <= 0 or request.method != "GET":
        return False
    days_ago = (timezone.localdate() - event.date).days
    # days_ago == 0 (race day) is included: race day is peak traffic and
    # invalidation on results import keeps entries fresh elsewhere.
    return 0 <= days_ago <= days


def index(request, year, race_slug, distance_slug, sequel_slug=None):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    if sequel_slug:
        sequel = get_object_or_404(Sequel, slug=sequel_slug)
    else:
        sequel = None
    cache_key = "event.{}.{}.{}.{}.{}".format(
        year, race_slug, distance_slug, sequel_slug, request.META["QUERY_STRING"]
    )
    with tracer.start_as_current_span("event: cache lookup"):
        cached = cache_lock.get(cache_key)
        if cached is not None:
            logger.info("cache HIT (warm): key=%s", cache_key)
            return cached
    with tracer.start_as_current_span("event: event lookup"):
        try:
            event = Event.objects.select_related(
                "race", "distance", "sequel", "timer"
            ).get(
                race__slug=race_slug,
                distance__slug=distance_slug,
                date__year=int(year),
                sequel=sequel,
            )
        except Exception:
            raise Http404("Matching event not found")
    # Cached path: past events within the config window render at most once
    # even under concurrent load (single-flight lock in cache_lock)
    with tracer.start_as_current_span("event: cacheability"):
        cacheable = _is_cacheable(event, request)
    if cacheable:
        return cache_lock.get_or_render(
            cache_key, lambda: _render_event(request, event, sequel, qstring)
        )
    return _render_event(request, event, sequel, qstring)


def _render_event(request, event, sequel, qstring):
    with tracer.start_as_current_span("event: build results"):
        page = get_page(qstring)
        category = get_category(qstring)
        division = get_division(qstring)
        shared.set_distance_display_name(event.distance, sequel)
        with tracer.start_as_current_span("event: samerace + team categories"):
            races = shared.create_samerace_list(event.race)
            team_categories = shared.get_team_categories(event)
        with tracer.start_as_current_span("event: hill/relay/phototag/wheelchair dicts"):
            hill_dict = get_hill_dict(event)
            relay_dict = get_relay_dict(event)
            dbphototags = list(Phototag.objects.filter(event=event).values_list("tag", flat=True))
            phototags = [x for x in dbphototags if x.isdigit()]
            wheelchair_results = Wheelchairresult.objects.filter(event=event)
        with tracer.start_as_current_span("event: pages"):
            pages = shared.get_pages(
                event,
                page,
                team_categories,
                hill_dict=hill_dict,
                wheelchair_results=wheelchair_results,
                relay_dict=relay_dict,
            )
        if page == "Wheelchair":
            # Wheelchairresult has no rwmember FK, so results can never be an
            # RW member's first event; annotate False so get_results can read it.
            all_results = Wheelchairresult.objects.filter(event=event).annotate(
                isrwfirst=Value(False, output_field=BooleanField())
            )
            hasage = False
            with tracer.start_as_current_span("event: results queryset"):
                all_results = list(
                    all_results.values(
                        "place",
                        "bib",
                        "athlete",
                        "gender",
                        "city",
                        "guntime",
                        "chiptime",
                        "category__name",
                        "category__ismasters",
                        "event_id",
                        "isrwfirst",
                    )
                )
                for r in all_results:
                    r["age"] = None
                    r["division"] = ""
                    r["isrwpb"] = False
        else:
            all_results = Result.objects.filter(event=event)
            # hasage must run before any annotation: otherwise the EXISTS
            # subquery annotation bloats what should be a cheap probe query
            # (issue #436).
            with tracer.start_as_current_span("event: results queryset"):
                hasage = all_results.hasage(event)
                # Materialize plain dicts instead of model instances: the row
                # loop only reads these fields, and skipping per-object model
                # instantiation + descriptor access was worth ~250ms per
                # 1800-row cold render (2026-11-06 profiling, see worklog).
                all_results = list(
                    all_results.values(
                        "place",
                        "bib",
                        "athlete",
                        "gender",
                        "age",
                        "city",
                        "guntime",
                        "chiptime",
                        "division",
                        "isrwpb",
                        "rwmember_id",
                        "rwmember__joindate",
                        "category__name",
                        "category__ismasters",
                        "event_id",
                    )
                )
                # isrwfirst in Python instead of a per-row correlated EXISTS
                # subquery in SQL (saves ~12ms SELECT + plan cost per cold
                # render): first = member's earliest event dated on/after
                # their join date, and this event is it. Same-date events
                # both count as first, matching the old `date <` semantics.
                _mark_isrwfirst(all_results, event.date)
        # Materialize splits once: truthiness, max, microseconds set, and the
        # per-place map all derive from this single list (one DB round-trip).
        with tracer.start_as_current_span("event: splits"):
            event_splits = list(Split.objects.filter(event=event))
        all_split_microseconds = {x.split_time.microseconds for x in event_splits if x.split_time}
        splits_have_microseconds = [x for x in all_split_microseconds if x != 0]
        results, max_splits, guntimes_have_microseconds = get_results(
            event,
            all_results,
            page,
            category,
            division,
            hill_dict,
            phototags,
            relay_dict,
            event_splits,
            splits_have_microseconds,
        )
        split_headings = get_split_headings(event, max_splits)
    hasdivision = False
    if event.race.slug == "endurrun":
        hasdivision = True
    with tracer.start_as_current_span("event: filters"):
        with tracer.start_as_current_span("event: category filter"):
            category_filter = get_category_filter(event, category, division)
        with tracer.start_as_current_span("event: distance filter"):
            distance_filter = get_distance_filter(event, races)
        with tracer.start_as_current_span("event: division filter"):
            division_filter = get_division_filter(event, division, category)
        with tracer.start_as_current_span("event: year filter"):
            year_filter = get_year_filter(event, races)
        filters = {
            "category_filter": category_filter,
            "distance_filter": distance_filter,
            "division_filter": division_filter,
            "year_filter": year_filter,
        }
        event_json = get_event_json(event)
    with tracer.start_as_current_span("event: ad/series/post"):
        ad = get_ad()
        series = get_series(event=event)
        process_post(request)
    with tracer.start_as_current_span("event: context"):
        race_logo_slug = utils.get_race_logo_slug(event.race.slug)
        extra_name = get_extra_name(event)
        show_category = len(filters["category_filter"].choices) > 5
        show_age = hasage and not show_category
        show_chip = bool(results and results[0].chiptime)
        # loop-invariant flags: the row loop used to re-resolve these
        # expressions (event attributes, truthiness of lists) for every row
        show_youtube = bool(event_json.youtube_id) and event_json.youtube_offset_seconds is not None
        context = {
            "show_youtube": show_youtube,
            "show_photos": bool(phototags),
            "flickrsearchstr": event_json.flickrsearchstr,
            "event_distance_name": event_json.distance.name,
            "show_category": show_category,
            "show_age": show_age,
            "show_chip": show_chip,
            "event": event_json,
            "filters": filters,
            "page": page,
            "pages": pages,
            "results": results,
            "hasage": hasage,
            "hasdivision": hasdivision,
            "hill_dict": hill_dict,
            "split_headings": split_headings,
            "extra_name": extra_name,
            "phototags": phototags,
            "guntimes_have_microseconds": guntimes_have_microseconds,
            "splits_have_microseconds": splits_have_microseconds,
            "ad": ad,
            "series": series,
            "race_logo_slug": race_logo_slug,
            "noindex": bool(qstring),
        }
    row_flags = {
        "show_category": show_category,
        "show_age": show_age,
        "show_chip": show_chip,
        "hasdivision": hasdivision,
        "hill_dict": hill_dict,
        "show_photos": bool(phototags),
        "show_youtube": bool(event_json.youtube_id) and event_json.youtube_offset_seconds is not None,
        "event_distance_name": conditional_escape(event_json.distance.name),
        "flickrsearchstr": conditional_escape(event_json.flickrsearchstr),
        "event_date_year": event.date.year,
    }
    # Per-bib/per-URL caches: photo and youtube cells are identical across
    # thousands of rows except for the bib/URL, so each is built once.
    row_flags["photo_cells"] = {}
    row_flags["youtube_cells"] = {}
    # NOTE: unorthodox — the entire results table is built as one HTML
    # string in Python and dropped into the page with |safe, instead of
    # being rendered by the template. Rationale: the DTL row loop was the
    # dominant cost of cold event-page renders (~500-700ms of template
    # lookups for 1800+ rows); building rows in Python with
    # conditional_escape cut that to ~130ms. ALL result data passes
    # through conditional_escape/_e in _build_row_html and
    # _build_table_html, so the |safe substitution is safe as long as
    # every value added there is escaped. The 5 golden event pages
    # (see rrw docs) guard this output byte-for-byte. If you add a cell,
    # add it in _build_row_html AND the golden files, not the template.
    row_flags["phototags"] = bool(phototags)
    with tracer.start_as_current_span("event: render table (python)"):
        rows_html = "".join(_build_row_html(r, row_flags) for r in context["results"])
        context["results_table"] = _build_table_html(rows_html, row_flags, split_headings)
    with tracer.start_as_current_span("event: template render"):
        html = render(request, "racedbapp/event.html", context).content.decode("utf-8")
    return HttpResponse(html)


def _e(v):
    """HTML-escape a value; empty string for False/None."""
    return conditional_escape(v) if v else ""


def _mark_isrwfirst(results, event_date):
    """Set isrwfirst on result dicts in place: True if this is the member's
    first event (by date) as a member (event date >= rwmember.joindate).

    Computed in Python with one grouped MIN query instead of a per-row
    correlated EXISTS subquery in SQL (2026-11-06: ~12ms SELECT per cold
    render on an 1800-row event). Same-date events both count as first,
    matching the original `date <` EXISTS semantics.
    """
    member_ids = {r["rwmember_id"] for r in results if r["rwmember_id"]}
    if member_ids:
        first_dates = dict(
            Result.objects.filter(
                rwmember_id__in=member_ids,
                event__date__gte=F("rwmember__joindate"),
            )
            .values("rwmember_id")
            .annotate(first=Min("event__date"))
            .values_list("rwmember_id", "first")
        )
    else:
        first_dates = {}
    for r in results:
        rid = r["rwmember_id"]
        r["isrwfirst"] = (
            rid is not None
            and event_date >= r["rwmember__joindate"]
            and first_dates.get(rid) == event_date
        )


def _build_row_html(r, flags):
    """Prebuilt-HTML variant of the event results row.

    All interpolated values are escaped via conditional_escape; flags are
    render-invariant and precomputed. Mirrors event.html's row markup.
    """
    show_category = flags["show_category"]
    show_age = flags["show_age"]
    show_chip = flags["show_chip"]
    hasdivision = flags["hasdivision"]
    hill_dict = flags["hill_dict"]
    show_photos = flags["show_photos"]
    show_youtube = flags["show_youtube"]
    name = _e(r.name)
    if r.member:
        name = f'<a href="/member/{conditional_escape(r.member.slug)}/">{name}</a>'
    if r.gender_place == 1:
        name += f'<i class="fas fa-trophy fa-icon-1st-oa" title="1st Overall ({_e(r.gender)})"></i>'
    elif r.gender_place == 2:
        name += f'<i class="fas fa-medal fa-icon-2nd-oa" title="2nd Overall ({_e(r.gender)})"></i>'
    elif r.gender_place == 3:
        name += f'<i class="fas fa-medal fa-icon-3rd-oa" title="3rd Overall ({_e(r.gender)})"></i>'
    if r.masters_place == 1:
        name += f'<i class="fas fa-medal fa-icon-1st-master" title="1st Master ({_e(r.gender)})"></i>'
    if r.isrwpb and r.member:
        name += f'<i class="fas fa-stopwatch fa-icon-pb" title="RW PB for the {flags["event_distance_name"]}"></i>'
    if r.isrwfirst:
        name += '<i class="fa-solid fa-hand-wave fa-icon-firstrace" title="Welcome new RW member!"></i>'
    if r.relay_team:
        name += f'<i class="fas fa-users" title="{_e(r.relay_team)}"></i>'
    photo_cell = ""
    if show_photos:
        if r.hasphotos:
            # bib is a race number (digits): no escaping needed, cached per bib
            photo_cell = flags["photo_cells"].get(r.bib)
            if photo_cell is None:
                photo_cell = (
                    f'<td class="text-center"><a href="https://www.flickr.com/photos/runwaterloo/tags/{flags["flickrsearchstr"]},{r.bib}" target="_blank"><i class="fas fa-camera"></i></a></td>'
                )
                flags["photo_cells"][r.bib] = photo_cell
        else:
            photo_cell = "<td></td>"
    youtube_cell = ""
    if show_youtube:
        if r.youtube_url:
            youtube_cell = flags["youtube_cells"].get(r.youtube_url)
            if youtube_cell is None:
                youtube_cell = f'<td class="text-center"><a href="{conditional_escape(r.youtube_url)}" target="_blank"><i class="fas fa-video"></i></a></td>'
                flags["youtube_cells"][r.youtube_url] = youtube_cell
        else:
            youtube_cell = "<td></td>"
    if hill_dict:
        prime_cell = f'<td class="text-center">{_e(r.prime)}</td>'
    else:
        prime_cell = ""
    if show_category:
        category_cells = (
            f'<td class="text-center">{_e(r.category)}</td>'
            f'<td class="text-center">{_e(r.category_place)}</td>'
        )
    else:
        category_cells = ""
    if show_age:
        age_cell = f'<td class="text-center">{_e(r.age)}</td>'
    else:
        age_cell = ""
    if hasdivision:
        if r.division != "Guest":
            d = conditional_escape(r.division)
            division_cell = f'<td class="text-left"><a href="/endurrun/{d.lower()}/?year={flags["event_date_year"]}">{d}</a></td>'
        else:
            division_cell = f'<td class="text-left">{_e(r.division)}</td>'
    else:
        division_cell = ""
    chip_cell = f'<td class="text-center">{_e(r.chip_display)}</td>' if show_chip else ""
    # place/bib/time/pace/splits are generated by this view (digits and
    # formatted times, no user text); gender/category/city/prime/division
    # come from the DB and stay escaped.
    split_html = "".join(f'<td class="text-center">{c}</td>' for c in r.split_cells)
    # One row per line: keeps the emitted HTML readable (djlint-style page
    # source) at no measurable join cost.
    return (
        f'<tr><td class="text-center">{r.place_display}</td>'
        f'<td class="text-center">{r.bib}</td>'
        f'<td class="text-left">{name}</td>'
        f'{photo_cell}{youtube_cell}'
        f'<td class="text-center">{r.time_display}</td>'
        f'{prime_cell}'
        f'<td class="text-center">{_e(r.gender)}</td>'
        f'<td class="text-center">{r.gender_place}</td>'
        f'{category_cells}{age_cell}{division_cell}'
        f'<td class="text-center">{r.pace}</td>'
        f'{chip_cell}'
        f'<td class="text-left">{_e(r.city)}</td>'
        f'{split_html}</tr>\n'
    )


def _build_table_html(rows, flags, split_headings):
    """Assemble the entire results table (thead + tbody) as one HTML string.

    Mirrors the results-table markup in event.html. Row cells are assumed
    pre-escaped by _build_row_html; split_headings are escaped here.
    """
    f = flags
    head = [
        '<table class="table table-bordered table-condensed table-striped table-hover">',
        '<thead>',
        '<tr class="info">',
        '<th class="text-center" scope="col">#</th>',
        '<th class="text-center" scope="col">Bib</th>',
        '<th class="text-left" scope="col">Name</th>',
    ]
    if f["phototags"]:
        head.append('<th class="text-center" scope="col"><i class="fas fa-camera"></i></th>')
    if f["show_youtube"]:
        head.append('<th class="text-center" scope="col"><i class="fas fa-video"></i></th>')
    head.append('<th class="text-center" scope="col">Time</th>')
    if f["hill_dict"]:
        head.append('<th class="text-center" scope="col">Hill Sprint</th>')
    head.append('<th class="text-center" scope="col">G</th>')
    head.append('<th class="text-center" scope="col">GP</th>')
    if f["show_category"]:
        head.append('<th class="text-center" scope="col">Cat</th>')
        head.append('<th class="text-center" scope="col">CP</th>')
    if f["show_age"]:
        head.append('<th class="text-center" scope="col">Age</th>')
    if f["hasdivision"]:
        head.append('<th class="text-left" scope="col">Division</th>')
    head.append('<th class="text-center" scope="col">Pace</th>')
    if f["show_chip"]:
        head.append('<th class="text-center" scope="col">Chip Time</th>')
    head.append('<th class="text-left" scope="col">City</th>')
    for sh in split_headings:
        head.append(f'<th class="text-center">{conditional_escape(sh)}</th>')
    head.append('</tr>\n</thead>\n<tbody>\n')
    return "\n".join(head) + rows + "</tbody></table>"


def get_event_json(event):
    named_event = namedtuple(
        "ne",
        [
            "id",
            "city",
            "date",
            "flickrsearchstr",
            "flickrsetid",
            "resultsurl",
            "youtube_id",
            "youtube_offset_seconds",
            "race",
            "distance",
            "sequel",
            "medals",
            "timer",
            "custom_logo_url",
        ],
    )
    named_race = namedtuple("nr", ["name", "shortname", "slug"])
    flickrsearchstr = "{}-{}-{}".format(event.date.year, event.race.slug, event.distance.slug)
    if event.sequel:
        flickrsearchstr += event.sequel.slug
    flickrsearchstr = flickrsearchstr.replace("-", "").replace("_", "")
    this_race = named_race(event.race.name, event.race.shortname, event.race.slug)
    shared.set_distance_display_name(event.distance, getattr(event, "sequel", None))
    event_json = named_event(
        event.id,
        event.city,
        event.date,
        flickrsearchstr,
        event.flickrsetid,
        event.resultsurl,
        event.youtube_id,
        event.youtube_offset_seconds,
        this_race,
        event.distance,
        event.sequel,
        event.medals,
        event.timer,
        event.custom_logo_url,
    )
    return event_json


def get_category_counts(event, division):
    """Counts for the category filter, in two grouped queries instead of 7:
    one GROUP BY gender pass for genders + masters (+ totals), one for
    categories. Returns (genders, masters, categories, total_count)."""
    all_results = Result.objects.filter(event=event)
    if division != "All":
        all_results = all_results.filter(division=division)
    masters_q = Q(category__ismasters=True) | Q(age__gte=40)
    gender_counts = (
        all_results.values("gender")
        .annotate(
            count=Count("id"),
            masters_count=Count("id", filter=masters_q),
        )
        .order_by("gender")
    )
    genders = []
    masters = []
    total_count = 0
    masters_total = 0
    for g in gender_counts:
        total_count += g["count"]
        masters_total += g["masters_count"]
        if g["gender"] == "F":
            genders.append({"category__name": "Female", "count": g["count"]})
        elif g["gender"] == "M":
            genders.append({"category__name": "Male", "count": g["count"]})
        elif g["gender"] == "NB":
            genders.append({"category__name": "Nonbinary", "count": g["count"]})
        if g["masters_count"] > 0 and g["gender"] in ("F", "M", "NB"):
            masters.append(
                {"category__name": f"{g['gender']}-Masters", "count": g["masters_count"]}
            )
    if masters_total > 0:
        masters.insert(0, {"category__name": "Masters", "count": masters_total})
    categories = (
        all_results.exclude(category__name="")
        .values("category__name")
        .annotate(count=Count("category__name"))
        .order_by("category__name")
    )
    return genders, masters, categories, total_count


def get_divisions(event, category):
    all_results = Result.objects.filter(event=event)
    if category != "All":
        if category in ("Female", "Male"):
            all_results = all_results.filter(gender=category[0])
        elif category == "Masters":
            all_results = all_results.filter(Q(category__ismasters=True) | Q(age__gte=40))
        elif category == "F-Masters":
            all_results = all_results.filter(gender="F").filter(
                Q(category__ismasters=True) | Q(age__gte=40)
            )
        elif category == "M-Masters":
            all_results = all_results.filter(gender="M").filter(
                Q(category__ismasters=True) | Q(age__gte=40)
            )
        elif category == "NB-Masters":
            all_results = all_results.filter(gender="NB").filter(
                Q(category__ismasters=True) | Q(age__gte=40)
            )
        else:
            all_results = all_results.filter(category__name=category)
    divisions = (
        all_results.exclude(division="")
        .values("division")
        .order_by("division")
        .annotate(count=Count("division"))
        .order_by("-division")
    )
    return divisions


def get_hill_dict(event):
    hill_dict = False
    if event.race.slug == "baden-road-races":
        if event.distance.slug == "7-mi":
            hill_results = Prime.objects.filter(event=event)
            hill_dict = {}
            for r in hill_results:
                hill_dict[r.place] = r.time
    return hill_dict


def get_page(qstring):
    page = "Overall"
    if "hill" in qstring:
        page = "Hill Sprint"
    elif "wheelchair" in qstring:
        page = "Wheelchair"
    return page


def get_category(qstring):
    category = "All"
    if "filter" in qstring:
        category = qstring["filter"][0]
    return category


def get_division(qstring):
    division = "All"
    if "division" in qstring:
        division = qstring["division"][0]
        if division not in ("Ultimate", "Sport", "Relay", "Guest"):
            raise Http404('Division "{}" is not valid'.format(division))
    return division


def get_distance_filter(event, races):
    # Only what's needed to build choices: skip full Event/distance model
    # instantiation (select_related pulled whole rows just to read 4 fields).
    events = list(
        Event.objects.select_related("distance", "sequel")
        .filter(race__in=races, date__year=event.date.year)
        .order_by("date", "-distance__km")
    )
    choices = []
    for e in events:
        display_name = e.sequel.name if e.sequel else e.distance.name
        if display_name == event.distance.display_name:
            continue
        url = "/event/{}/{}/{}/".format(
            event.date.year,
            event.race.slug,
            e.distance.slug,
        )
        if e.sequel:
            url += f"{e.sequel.slug}/"
        choices.append(Choice(display_name, url))
    if event.race.slug == "baden-road-races":
        durelaycount = Durelay.objects.filter(year=event.date.year).count()
        if durelaycount > 0:
            choices.append(Choice("Sprint Duathlon Relay", "/durelay/{}/".format(event.date.year)))
    distance_filter = Filter(event.distance.display_name, choices)
    return distance_filter


def get_year_filter(event, races):
    # Query Event (few dozen rows) instead of Result (thousands), keeping the
    # original semantics: only years where this race+distance actually had
    # results, mapped to that year's race slug.
    # Exists() probe instead of result__isnull=False: no event x results
    # JOIN + DISTINCT (that scan costs ~20ms); the correlated EXISTS stops at
    # one indexed row check per event.
    dates = (
        Event.objects.filter(
            race__in=races,
            distance=event.distance,
        )
        .filter(Exists(Result.objects.filter(event=OuterRef("pk"))))
        .order_by("-date")
        .values_list("date", "race__slug")
        .distinct()
    )
    choices = []
    for d in dates:
        year = d[0].year
        if year == event.date.year:
            continue
        choices.append(Choice(year, "/event/{}/{}/{}/".format(year, d[1], event.distance.slug)))
    year_filter = Filter(event.date.year, choices)
    return year_filter


def get_category_filter(event, category, division):
    genders, masters, categories, total_count = get_category_counts(event, division)
    all_categories = genders + masters + list(categories)
    choices = []
    base_url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    if event.sequel:
        base_url += f"{event.sequel.slug}/"
    if category == "All":
        current = "All ({})".format(total_count)
    else:
        try:
            category_count = [
                x["count"] for x in all_categories if x["category__name"] == category
            ][0]
        except Exception:
            category_count = 0
        current = "{} ({})".format(category, category_count)
        if division == "All":
            url = base_url
            choices.append(
                Choice(
                    "All ({})".format(total_count),
                    url,
                )
            )
        else:
            url = f"{base_url}?division={division}"
            choices.append(
                Choice(
                    "All ({})".format(total_count),
                    url,
                )
            )
    for a in all_categories:
        if a["category__name"] == category:
            continue
        if division == "All":
            url = f"{base_url}?filter={a['category__name']}"
            choices.append(
                Choice(
                    "{} ({})".format(a["category__name"], a["count"]),
                    url,
                )
            )
        else:
            url = f"{base_url}?filter={a['category__name']}&division={division}"
            choices.append(
                Choice(
                    "{} ({})".format(a["category__name"], a["count"]),
                    url,
                )
            )
    category_filter = Filter(current, choices)
    return category_filter


def get_division_filter(event, division, category):
    divisions = get_divisions(event, category)
    if len(divisions) == 0:
        return False
    all_results = filter_results_by_category(Result.objects.filter(event=event), category)
    total_count = all_results.count()
    choices = []
    base_url = f"/event/{event.date.year}/{event.race.slug}/{event.distance.slug}/"
    if event.sequel:
        base_url += f"{event.sequel.slug}/"
    if division == "All":
        current = "All ({})".format(total_count)
    else:
        division_count = get_division_count(divisions, division)
        current = "{} ({})".format(division, division_count)
        if category == "All":
            url = base_url
            choices.append(
                Choice("All ({})".format(total_count), url),
            )
        else:
            url = f"{base_url}?filter={category}"
            choices.append(Choice("All ({})".format(total_count), url))
    for d in divisions:
        if d["division"] == division:
            continue
        if category == "All":
            url = f"{base_url}?division={d['division']}"
            choices.append(Choice("{} ({})".format(d["division"], d["count"]), url))
        else:
            url = f"{base_url}?filter={category}&division={d['division']}"
            choices.append(Choice("{} ({})".format(d["division"], d["count"]), url))
    division_filter = Filter(current, choices)
    return division_filter


def get_division_count(divisions, division):
    """Return the count for the given division name from a list of division dicts"""
    for d in divisions:
        if d["division"] == division:
            return d["count"]
    return 0


def filter_results_by_category(queryset, category):
    if category == "All":
        return queryset
    if category in ("Female", "Male"):
        return queryset.filter(gender=category[0])
    if category == "Masters":
        return queryset.filter(Q(category__ismasters=True) | Q(age__gte=40))
    if category == "F-Masters":
        return queryset.filter(gender="F").filter(Q(category__ismasters=True) | Q(age__gte=40))
    if category == "M-Masters":
        return queryset.filter(gender="M").filter(Q(category__ismasters=True) | Q(age__gte=40))
    if category == "NB-Masters":
        return queryset.filter(gender="NB").filter(Q(category__ismasters=True) | Q(age__gte=40))
    return queryset.filter(category__name=category)


def get_results(
    event,
    all_results,
    page,
    category,
    division,
    hill_dict,
    phototags,
    relay_dict,
    event_splits,
    splits_have_microseconds,
):
    named_result = namedtuple(
        "nr",
        [
            "place",
            "bib",
            "name",
            "relay_team",
            "gender",
            "gender_place",
            "category",
            "category_place",
            "age",
            "division",
            "guntime",
            "prime",
            "chiptime",
            "city",
            "ismasters",
            "splits",
            "member",
            "hasphotos",
            "youtube_url",
            "masters_place",
            "isrwpb",
            "isrwfirst",
            # display-ready values precomputed here so the template does no
            # filter calls per cell
            "place_display",
            "time_display",
            "chip_display",
            "pace",
            "split_cells",
        ],
    )
    results = []
    with tracer.start_as_current_span("event: relay dict + split map"):
        endurrun_relay_dict = get_endurrun_relay_dict(event)
        gender_place_dict = defaultdict(int)
        masters_place_dict = defaultdict(int)
        category_place_dict = {}
        splits_by_place = {}
        for split in event_splits:
            splits_by_place.setdefault(split.place, {})[split.split_num] = split.split_time
        max_splits = False
        empty_splits = []
        if event_splits:
            max_splits = int(max(x.split_num for x in event_splits))
            empty_splits = [named_split(i, "") for i in range(1, max_splits + 1)]
            empty_split_cells = [""] * max_splits
    km = event.distance.km
    guntimes_have_microseconds = set()
    membership = shared.get_membership(event=event)
    with tracer.start_as_current_span("event: build rows"):
        has_youtube = False
        if event.youtube_id and event.youtube_offset_seconds is not None:
            has_youtube = True
            LEAD_TIME_SECONDS = 7
            youtube_duration_seconds = event.youtube_duration_seconds
        with tracer.start_as_current_span("event: row loop"):
            for r in all_results:
                relay_team = False
                ismasters = False
                if r["category__ismasters"]:
                    ismasters = True
                else:
                    if page != "Wheelchair":
                        if r["age"]:
                            if r["age"] >= 40:
                                ismasters = True
                masters_place = False
                gender_place = ""
                if r["gender"] != "":
                    gender_place_dict[r["gender"]] += 1
                    gender_place = gender_place_dict[r["gender"]]
                    if ismasters:
                        masters_place_dict[r["gender"]] += 1
                        masters_place = masters_place_dict[r["gender"]]
                category_place = ""
                if r["category__name"] != "":
                    if r["category__name"] in category_place_dict:
                        category_place_dict[r["category__name"]] += 1
                        category_place = category_place_dict[r["category__name"]]
                    else:
                        category_place_dict[r["category__name"]] = 1
                        category_place = 1
                if relay_dict:
                    if r["place"] in relay_dict:
                        relay_team = relay_dict[r["place"]]
                elif r["athlete"] in endurrun_relay_dict:
                    relay_team = endurrun_relay_dict[r["athlete"]]
                age = ""
                if page != "Wheelchair":
                    if r["age"]:
                        age = r["age"]
                guntime = chiptime = ""
                if r["place"] < 990000:
                    guntime = r["guntime"]
                    if guntime and guntime.microseconds != 0:
                        guntimes_have_microseconds.add(guntime.microseconds)
                    if r["chiptime"]:
                        chiptime = r["chiptime"]
                try:
                    prime = hill_dict[r["place"]]
                except Exception:
                    prime = ""
                else:
                    prime = get_short_time(prime)
                if page == "Wheelchair":
                    result_division = ""
                else:
                    result_division = r["division"]
                splits = []
                split_cells = []
                if event_splits:
                    row_splits = splits_by_place.get(r["place"])
                    if row_splits is None:
                        # shared immutable lists: identical for every row
                        # without split data (template only reads)
                        splits = empty_splits
                        split_cells = empty_split_cells
                    else:
                        splits = [
                            named_split(
                                i,
                                get_short_time(split_time) if split_time is not None else "",
                            )
                            for i, split_time in (
                                (i, row_splits.get(i)) for i in range(1, max_splits + 1)
                            )
                        ]
                        if splits_have_microseconds:
                            split_cells = [
                                show_str_decimal(st.split_time)
                                if st.split_time != ""
                                else ""
                                for st in splits
                            ]
                        else:
                            split_cells = [st.split_time for st in splits]
                member = shared.get_member(
                    _MemberKey(r["athlete"], event, r["place"]), membership
                )
                pace = ""
                if guntime:
                    pace = get_pace(guntime, km)
                hasphotos = False
                youtube_url = False
                if has_youtube and r["place"] < 990000:
                    video_position_seconds = guntime.total_seconds() - event.youtube_offset_seconds
                    if video_position_seconds >= 0:
                        if video_position_seconds > LEAD_TIME_SECONDS:
                            video_position_seconds -= LEAD_TIME_SECONDS
                        else:
                            video_position_seconds = 1
                        minutes = int(video_position_seconds // 60)
                        seconds = int(video_position_seconds % 60)
                        video_position = "{}m{}s".format(minutes, seconds)
                        youtube_url = "https://youtu.be/{}?t={}".format(event.youtube_id, video_position)
                        # set youtube_url back to false if past end of video
                        if youtube_duration_seconds:
                            if video_position_seconds >= youtube_duration_seconds:
                                youtube_url = False
                if r["bib"] in phototags:
                    hasphotos = True
                isrwpb = r["isrwpb"]
                results.append(
                    named_result(
                        place=r["place"],
                        bib=r["bib"],
                        name=r["athlete"],
                        relay_team=relay_team,
                        gender=r["gender"],
                        gender_place=gender_place,
                        category=r["category__name"],
                        category_place=category_place,
                        age=age,
                        division=result_division,
                        guntime=guntime,
                        prime=prime,
                        chiptime=chiptime,
                        city=r["city"],
                        ismasters=ismasters,
                        splits=splits,
                        member=member,
                        hasphotos=hasphotos,
                        youtube_url=youtube_url,
                        masters_place=masters_place,
                        isrwpb=isrwpb,
                        isrwfirst=r["isrwfirst"],
                        place_display="",
                        time_display="",
                        chip_display="",
                        pace=pace,
                        split_cells=split_cells,
                    )
                )
    with tracer.start_as_current_span("event: filter results"):
        results = filter_results(results, category, division)
        if page == "Hill Sprint":
            results = get_hill_results(results, named_result)
    with tracer.start_as_current_span("event: display fields"):
        # display strings that depend on the complete guntimes set; the
        # template gets ready-to-print values with no filter calls
        has_micro = len(guntimes_have_microseconds) > 0
        out = []
        for r in results:
            if r.guntime:
                time_display = round_up(r.guntime) if has_micro else r.guntime
            else:
                time_display = r.guntime
            if r.chiptime:
                chip_display = round_up(r.chiptime) if has_micro else r.chiptime
            else:
                chip_display = r.chiptime
            out.append(
                r._replace(
                    place_display=get_place(r.place),
                    time_display=time_display,
                    chip_display=chip_display,
                )
            )
        results = out
    return results, max_splits, guntimes_have_microseconds




def get_endurrun_relay_dict(event):
    endurrun_relay_dict = {}
    if event.race.slug == "endurrun":
        if event.distance.slug == "half-marathon":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st1", "name")
            )
        if event.distance.slug == "15-km":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st2", "name")
            )
        if event.distance.slug == "30-km":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st3", "name")
            )
        if event.distance.slug == "10-mi":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st4", "name")
            )
        if event.distance.slug == "25_6-km":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st5", "name")
            )
        if event.distance.slug == "10-km":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st6", "name")
            )
        if event.distance.slug == "marathon":
            endurrun_relay_dict = dict(
                Endurteam.objects.filter(year=event.date.year).values_list("st7", "name")
            )
    return endurrun_relay_dict


def get_short_time(orig_time):
    short_time = str(orig_time).lstrip("0:")
    if len(short_time) == 2:
        short_time = "0:{}".format(short_time)
    return short_time


def filter_results(results, category, division):
    if category == "Female":
        results = [x for x in results if x.gender == "F"]
    elif category == "Male":
        results = [x for x in results if x.gender == "M"]
    elif category == "Nonbinary":
        results = [x for x in results if x.gender == "NB"]
    elif category == "Masters":
        results = [x for x in results if x.ismasters]
    elif category == "F-Masters":
        results = [x for x in results if x.ismasters and x.gender == "F"]
    elif category == "M-Masters":
        results = [x for x in results if x.ismasters and x.gender == "M"]
    elif category == "NB-Masters":
        results = [x for x in results if x.ismasters and x.gender == "NB"]
    elif category != "All":
        results = [x for x in results if x.category == category]
    if division != "All":
        results = [x for x in results if x.division == division]
    return results


def get_hill_results(results, named_result):
    results = [x for x in results if x.prime != ""]
    hill_results = []
    for i, r in enumerate(results, 1):
        prime = r.prime
        if len(prime) == 4:
            prime = "0{}".format(prime)
        hill_results.append(r._replace(place=i, prime=prime))
    hill_results = sorted(hill_results, key=attrgetter("prime", "place"))
    return hill_results


def get_extra_name(event):
    extra_name = ""
    if event.race.slug == "endurrun":
        if event.distance.slug == "half-marathon":
            extra_name = "Stage 1 - "
        elif event.distance.slug == "15-km":
            extra_name = "Stage 2 - "
        elif event.distance.slug == "30-km":
            extra_name = "Stage 3 - "
        elif event.distance.slug == "10-mi":
            extra_name = "Stage 4 - "
        elif event.distance.slug == "25_6-km":
            extra_name = "Stage 5 - "
        elif event.distance.slug == "10-km":
            extra_name = "Stage 6 - "
        elif event.distance.slug == "marathon":
            extra_name = "Stage 7 - "
    return extra_name


def get_relay_dict(event):
    relay_dict = False
    relay_results = Relay.objects.filter(event=event).values_list("place", "relay_team")
    if len(relay_results) > 0:
        relay_dict = dict(relay_results)
    return relay_dict


def get_split_headings(event, max_splits):
    if event.distance.slug == "sprint-duathlon":
        split_headings = ["Run 1", "T1", "Cycle", "T2", "Run 2"]
    else:
        split_headings = []
        for i in range(1, max_splits + 1):
            split_headings.append("Split {}".format(i))
    return split_headings


def process_post(request):
    """If request is a POST it should send email"""
    if request.method == "POST":
        url = "https://{}{}".format(request.get_host(), request.get_full_path())
        user_name = request.POST.get("user_name")
        user_email = request.POST.get("user_email")
        message_text = request.POST.get("message_text")
        subject = "Automatic message from Run Waterloo to {}".format(user_name)
        email_to_address = Config.objects.get(name="email_to_address").value
        recipients = [email_to_address, user_email]
        body = ""
        body += "Thank you {} for your inquiry. We will review it and reply shortly.\n\n".format(
            user_name
        )
        body += "{}\n\n".format(message_text)
        body += url
        safe_enqueue(send_email_task, subject, body, recipients)


def get_ad():
    ad = False
    text = shared.get_config_value_or_false("ad_text")
    url = shared.get_config_value_or_false("ad_url")
    if text:
        if url:
            ad = Ad()
            ad.text = text
            ad.url = url
    return ad


class Ad:
    def __init__(self):
        self.text = False
        self.url = False
