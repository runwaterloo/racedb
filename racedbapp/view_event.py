from collections import defaultdict, namedtuple
from operator import attrgetter
from urllib import parse

from django.db.models import (
    BooleanField,
    Case,
    Count,
    Exists,
    F,
    Max,
    OuterRef,
    Q,
    Value,
    When,
)
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from racedbapp.shared.types import Choice, Filter
from racedbapp.tasks import send_email_task

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
from .shared import shared, utils

named_split = namedtuple("ns", ["split_num", "split_time"])


def index(request, year, race_slug, distance_slug, sequel_slug=None):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    page = get_page(qstring)
    category = get_category(qstring)
    division = get_division(qstring)
    if sequel_slug:
        sequel = get_object_or_404(Sequel, slug=sequel_slug)
    else:
        sequel = None
    try:
        event = Event.objects.select_related().get(
            race__slug=race_slug,
            distance__slug=distance_slug,
            date__icontains=year,
            sequel=sequel,
        )
    except Exception:
        raise Http404("Matching event not found")
    shared.set_distance_display_name(event.distance, sequel)
    races = shared.create_samerace_list(event.race)
    team_categories = shared.get_team_categories(event)
    hill_dict = get_hill_dict(event)
    relay_dict = get_relay_dict(event)
    dbphototags = list(Phototag.objects.filter(event=event).values_list("tag", flat=True))
    phototags = [x for x in dbphototags if x.isdigit()]
    wheelchair_results = Wheelchairresult.objects.filter(event=event)
    pages = shared.get_pages(
        event,
        page,
        team_categories,
        hill_dict=hill_dict,
        wheelchair_results=wheelchair_results,
        relay_dict=relay_dict,
    )
    if page == "Wheelchair":
        all_results = Wheelchairresult.objects.filter(event=event)
        hasage = False
    else:
        all_results = Result.objects.select_related().filter(event=event)
        all_results = annotate_isrwfirst(all_results)
        hasage = all_results.hasage(event)
    event_splits = Split.objects.filter(event=event)
    all_split_microseconds = {x.split_time.microseconds for x in event_splits if x.split_time}
    splits_have_microseconds = [x for x in all_split_microseconds if x != 0]
    results, max_splits = get_results(
        event,
        all_results,
        page,
        category,
        division,
        hill_dict,
        phototags,
        relay_dict,
        event_splits,
    )
    split_headings = get_split_headings(event, max_splits)
    hasdivision = False
    if event.race.slug == "endurrun":
        hasdivision = True
    extra_name = get_extra_name(event)
    filters = {
        "category_filter": get_category_filter(event, category, division),
        "distance_filter": get_distance_filter(event, races),
        "division_filter": get_division_filter(event, division, category),
        "year_filter": get_year_filter(event, races),
    }
    event_json = get_event_json(event)
    guntimes_have_microseconds = {
        x.guntime.microseconds for x in all_results if x.guntime.microseconds != 0
    }
    ad = get_ad()
    series = []
    all_series = Series.objects.all().order_by("year")
    for s in all_series:
        if event.id in [int(x.strip()) for x in s.event_ids.split(",")]:
            series.append(s)
    process_post(request)
    race_logo_slug = utils.get_race_logo_slug(event.race.slug)
    context = {
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
    }
    html = render(request, "racedbapp/event.html", context).content.decode("utf-8")
    return HttpResponse(html)


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
            "medals",
            "timer",
            "custom_logo_url",
        ],
    )
    named_race = namedtuple("nr", ["name", "shortname", "slug"])
    flickrsearchstr = (
        "{}-{}-{}".format(event.date.year, event.race.slug, event.distance.slug)
        .replace("-", "")
        .replace("_", "")
    )
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
        event.medals,
        event.timer,
        event.custom_logo_url,
    )
    return event_json


def get_masters(event, division):
    masters = []
    all_masters = Result.objects.filter(event=event).filter(
        Q(category__ismasters=True) | Q(age__gte=40)
    )
    if division != "All":
        all_masters = all_masters.filter(division=division)
    masters_count = all_masters.count()
    if masters_count > 0:
        masters.append({"category__name": "Masters", "count": masters_count})
        female_masters_count = all_masters.filter(gender="F").count()
        if female_masters_count > 0:
            masters.append({"category__name": "F-Masters", "count": female_masters_count})
        male_masters_count = all_masters.filter(gender="M").count()
        if male_masters_count > 0:
            masters.append({"category__name": "M-Masters", "count": male_masters_count})
        nonbinary_masters_count = all_masters.filter(gender="NB").count()
        if nonbinary_masters_count > 0:
            masters.append({"category__name": "NB-Masters", "count": nonbinary_masters_count})
    return masters


def get_genders(event, division):
    all_results = Result.objects.filter(event=event)
    if division != "All":
        all_results = all_results.filter(division=division)
    abbr_genders = (
        all_results.exclude(gender="")
        .values("gender")
        .order_by("gender")
        .annotate(count=Count("gender"))
        .order_by("gender")
    )
    genders = []
    for i in abbr_genders:
        if i["gender"] == "F":
            genders.append({"category__name": "Female", "count": i["count"]})
        elif i["gender"] == "M":
            genders.append({"category__name": "Male", "count": i["count"]})
        elif i["gender"] == "NB":
            genders.append({"category__name": "Nonbinary", "count": i["count"]})
    return genders


def get_categories(event, division):
    all_results = Result.objects.filter(event=event)
    if division != "All":
        all_results = all_results.filter(division=division)
    categories = (
        all_results.exclude(category__name="")
        .values("category__name")
        .order_by("category")
        .annotate(count=Count("category__name"))
        .order_by("category__name")
    )
    return categories


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
    events = list(
        Event.objects.select_related()
        .filter(race__in=races, date__icontains=event.date.year)
        .order_by("date", "-distance__km")
    )
    for e in events:
        shared.set_distance_display_name(e.distance, getattr(e, "sequel", None))
    choices = []
    for e in events:
        if e.distance.display_name == event.distance.display_name:
            continue
        url = "/event/{}/{}/{}/".format(
            event.date.year,
            event.race.slug,
            e.distance.slug,
        )
        if e.sequel:
            url += f"{e.sequel.slug}/"
        choices.append(Choice(e.distance.display_name, url))
    if event.race.slug == "baden-road-races":
        durelaycount = Durelay.objects.filter(year=event.date.year).count()
        if durelaycount > 0:
            choices.append(Choice("Sprint Duathlon Relay", "/durelay/{}/".format(event.date.year)))
    distance_filter = Filter(event.distance.display_name, choices)
    return distance_filter


def get_year_filter(event, races):
    rawresults = Result.objects.select_related().filter(
        event__race__in=races, event__distance=event.distance
    )
    dates = (
        rawresults.order_by("-event__date")
        .values_list("event__date", "event__race__slug")
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
    all_results = Result.objects.filter(event=event)
    if division != "All":
        all_results = all_results.filter(division=division)
    total_count = all_results.count()
    genders = get_genders(event, division)
    masters = get_masters(event, division)
    categories = get_categories(event, division)
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
        ],
    )
    results = []
    endurrun_relay_dict = get_endurrun_relay_dict(event)
    gender_place_dict = defaultdict(int)
    masters_place_dict = defaultdict(int)
    category_place_dict = {}
    splits_list = event_splits.values_list("place", "split_num", "split_time")
    splits_dict = {(a, b): c for a, b, c in splits_list}
    max_splits = False
    if event_splits:
        max_splits = int(event_splits.aggregate(Max("split_num"))["split_num__max"])
    membership = shared.get_membership(event=event)
    has_youtube = False
    if event.youtube_id and event.youtube_offset_seconds is not None:
        has_youtube = True
        LEAD_TIME_SECONDS = 7
        youtube_duration_seconds = event.youtube_duration_seconds
    for r in all_results:
        relay_team = False
        ismasters = False
        if r.category.ismasters:
            ismasters = True
        else:
            if page != "Wheelchair":
                if r.age:
                    if r.age >= 40:
                        ismasters = True
        masters_place = False
        gender_place = ""
        if r.gender != "":
            gender_place_dict[r.gender] += 1
            gender_place = gender_place_dict[r.gender]
            if ismasters:
                masters_place_dict[r.gender] += 1
                masters_place = masters_place_dict[r.gender]
        category_place = ""
        if r.category.name != "":
            if r.category.name in category_place_dict:
                category_place_dict[r.category.name] += 1
                category_place = category_place_dict[r.category.name]
            else:
                category_place_dict[r.category.name] = 1
                category_place = 1
        if relay_dict:
            if r.place in relay_dict:
                relay_team = relay_dict[r.place]
        elif r.athlete in endurrun_relay_dict:
            relay_team = endurrun_relay_dict[r.athlete]
        age = ""
        if page != "Wheelchair":
            if r.age:
                age = r.age
        guntime = chiptime = ""
        if r.place < 990000:
            guntime = r.guntime
            if r.chiptime:
                chiptime = r.chiptime
        try:
            prime = hill_dict[r.place]
        except Exception:
            prime = ""
        else:
            prime = get_short_time(prime)
        if page == "Wheelchair":
            result_division = ""
        else:
            result_division = r.division
        splits = []
        if event_splits:
            for i in range(1, max_splits + 1):
                try:
                    splits.append(named_split(i, get_short_time(splits_dict[(r.place, i)])))
                except Exception:
                    splits.append(named_split(i, ""))
        member = shared.get_member(r, membership)
        hasphotos = False
        youtube_url = False
        if has_youtube and r.place < 990000:
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
        if r.bib in phototags:
            hasphotos = True
        try:
            isrwpb = r.isrwpb
        except Exception:
            isrwpb = False
        results.append(
            named_result(
                r.place,
                r.bib,
                r.athlete,
                relay_team,
                r.gender,
                gender_place,
                r.category.name,
                category_place,
                age,
                result_division,
                guntime,
                prime,
                chiptime,
                r.city,
                ismasters,
                splits,
                member,
                hasphotos,
                youtube_url,
                masters_place,
                isrwpb,
                r.isrwfirst,
            )
        )
    results = filter_results(results, category, division)
    if page == "Hill Sprint":
        results = get_hill_results(results, named_result)
    return results, max_splits


def annotate_isrwfirst(queryset):
    # Annotate each result with isrwfirst: True if this is the member's first event (by date)
    # as a member (event date >= rwmember.joindate). False otherwise.
    earlier_event_exists = queryset.model.objects.filter(
        rwmember=OuterRef("rwmember"),
        event__date__lt=OuterRef("event__date"),
        event__date__gte=OuterRef("rwmember__joindate"),
    )
    # Annotate join date for comparison
    queryset = queryset.annotate(_joindate=F("rwmember__joindate"))
    return queryset.annotate(
        isrwfirst=Case(
            When(rwmember__isnull=True, then=Value(False)),
            When(event__date__lt=F("_joindate"), then=Value(False)),
            default=~Exists(earlier_event_exists),
            output_field=BooleanField(),
        )
    )


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
    hill_results = []
    results = [x for x in results if x.prime != ""]
    for i, r in enumerate(results, 1):
        prime = r.prime
        if len(prime) == 4:
            prime = "0{}".format(prime)
        hill_results.append(
            named_result(
                i,
                r.bib,
                r.name,
                r.relay_team,
                r.gender,
                r.gender_place,
                r.category,
                r.category_place,
                r.age,
                r.division,
                r.guntime,
                prime,
                r.chiptime,
                r.city,
                r.ismasters,
                r.splits,
                r.member,
                r.hasphotos,
                r.youtube_url,
                r.masters_place,
                r.isrwpb,
                r.isrwfirst,
            )
        )
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
        send_email_task.delay(subject, body, recipients)


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
