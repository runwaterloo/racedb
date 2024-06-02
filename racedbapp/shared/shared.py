from collections import namedtuple

from django.db.models import Q
from django.http import Http404

from racedbapp.shared.endurrun import get_member_endurrace, get_ultimate_finished_all_events
from racedbapp.shared.types import namedresult, namedteamrecord

from ..config import ValidRelayCategories
from ..models import (
    Config,
    Distance,
    Endurathlete,
    Endurraceresult,
    Event,
    Prime,
    Race,
    Relay,
    Result,
    Rwmember,
    Rwmembercorrection,
    Samerace,
    Teamcategory,
    Teamresult,
)
from ..view_relay import get_individual_results_dict, get_relay_results, get_team_results

def getwinnersdict():
    namedwinner = namedtuple("nw", ["athlete", "guntime"])
    malewinners = Result.objects.filter(gender="M", gender_place=1).values_list(
        "event_id", "athlete", "guntime"
    )
    malewinnersdict = {a: namedwinner(b, c) for a, b, c in malewinners}
    femalewinners = Result.objects.filter(gender="F", gender_place=1).values_list(
        "event_id", "athlete", "guntime"
    )
    femalewinnersdict = {a: namedwinner(b, c) for a, b, c in femalewinners}
    return malewinnersdict, femalewinnersdict


def get_race_records(race, distance, division_choice=False, individual_only=False)-> tuple[list, list | dict | None, list | None]:
    if not race:
        return [], None, None
    membership = get_membership()
    race = Race.objects.get(id=race.id)
    races = create_samerace_list(race)
    if distance.slug == "combined":
        events = []
        rawresults = Endurraceresult.objects.all()
        mrtime = rawresults.filter(gender="M").order_by("guntime")[:1][0].guntime
        mr = rawresults.filter(gender="M", guntime=mrtime).order_by("year")
        frtime = rawresults.filter(gender="F").order_by("guntime")[:1][0].guntime
        fr = rawresults.filter(gender="F", guntime=frtime).order_by("year")
        try:
            mmrtime = (
                rawresults.filter(gender="M", category__ismasters=True)
                .order_by("guntime")[:1][0]
                .guntime
            )
        except Exception:
            mmr = False
        else:
            mmr = rawresults.filter(
                gender="M", category__ismasters=True, guntime=mmrtime
            ).order_by("year")
        try:
            fmrtime = (
                rawresults.filter(gender="F", category__ismasters=True)
                .order_by("guntime")[:1][0]
                .guntime
            )
        except Exception:
            fmr = False
        else:
            fmr = rawresults.filter(
                gender="F", category__ismasters=True, guntime=fmrtime
            ).order_by("year")
    else:
        distance = Distance.objects.get(id=distance.id)
        events = Event.objects.filter(race__in=races, distance=distance)
        if division_choice and division_choice != "All" and race.slug == "endurrun":
            rawresults = Result.objects.filter(
                event__race=race, event__distance=distance, division=division_choice
            )
            if division_choice == "Ultimate":
                dates = rawresults.values_list("event__date", flat=True).distinct()
                years = {x.year for x in dates}
                ultimate_finished_all_events = get_ultimate_finished_all_events(years)
                results_to_include = []
                for r in rawresults:
                    try:
                        ultimate_athlete = Endurathlete.objects.get(
                            name=r.athlete,
                            division=division_choice,
                            year=r.event.date.year,
                        )
                    except:
                        continue
                    if ultimate_finished_all_events[r.event.date.year][
                        ultimate_athlete
                    ]:
                        results_to_include.append(r.id)
                rawresults = rawresults.filter(id__in=results_to_include)
        else:
            rawresults = Result.objects.filter(
                event__race__in=races, event__distance=distance
            )
        if rawresults.count() == 0:
            raise Http404("No results found for {}".format(distance))
        mrtime = rawresults.filter(gender="M").order_by("guntime")[:1][0].guntime
        mr = rawresults.filter(gender="M", guntime=mrtime).order_by("event__date")
        frtime = rawresults.filter(gender="F").order_by("guntime")[:1][0].guntime
        fr = rawresults.filter(gender="F", guntime=frtime).order_by("event__date")
        if race.slug != "endurrun":
            try:
                mmrtime = (
                    rawresults.filter(gender="M")
                    .filter(Q(category__ismasters=True) | Q(age__gte=40))
                    .order_by("guntime")[:1][0]
                    .guntime
                )
            except Exception:
                mmr = False
            else:
                mmr = (
                    rawresults.filter(gender="M", guntime=mmrtime)
                    .filter(Q(category__ismasters=True) | Q(age__gte=40))
                    .order_by("event__date")
                )
            try:
                fmrtime = (
                    rawresults.filter(gender="F")
                    .filter(Q(category__ismasters=True) | Q(age__gte=40))
                    .order_by("guntime")[:1][0]
                    .guntime
                )
            except Exception:
                fmr = False
            else:
                fmr = (
                    rawresults.filter(gender="F", guntime=fmrtime)
                    .filter(Q(category__ismasters=True) | Q(age__gte=40))
                    .order_by("event__date")
                )
        elif race.slug == "endurrun":
            try:
                mmrtime = (
                    rawresults.filter(gender="M", age__gte=40)
                    .order_by("guntime")[:1][0]
                    .guntime
                )
            except Exception:
                mmr = False
            else:
                mmr = rawresults.filter(
                    gender="M", age__gte=40, guntime=mmrtime
                ).order_by("event__date")
            try:
                fmrtime = (
                    rawresults.filter(gender="F", age__gte=40)
                    .order_by("guntime")[:1][0]
                    .guntime
                )
            except Exception:
                fmr = False
            else:
                fmr = rawresults.filter(
                    gender="F", age__gte=40, guntime=fmrtime
                ).order_by("event__date")
    records = []
    records += makerecords("Overall Male", mrtime, mr, distance, membership)
    records += makerecords("Overall Female", frtime, fr, distance, membership)
    if mmr:
        records += makerecords("Masters Male", mmrtime, mmr, distance, membership)
    if fmr:
        records += makerecords("Masters Female", fmrtime, fmr, distance, membership)
    if individual_only:
        return records

    team_records = []
    if race.slug == "laurier-loop" and distance.slug == "2_5-km":
        team_records = get_relay_records()
    else:
        team_categories = (
            Teamcategory.objects.all()
            .exclude(name="Family")
            .exclude(name="Open 8")
            .exclude(name="Masters 4")
            .exclude(name="Masters 5")
            .exclude(name="Open 10")
            .exclude(name="Open 4")
            .exclude(name="Open 15")
            .exclude(name="Corporate 5")
            .exclude(name="Corporate 3 Mixed")
            .exclude(name="Corporate 3 Men")
            .exclude(name="2 Person Relay")
            .exclude(name="4 Person Relay")
        )
        category_records = {}
        for event in events:
            winning_teams = Teamresult.objects.of_event(event)
            for w in winning_teams:
                for t in team_categories:
                    if w.team_category.name == t.name:
                        if t.name in category_records:
                            if w.total_time < category_records[t.name][0].total_time:
                                category_records[t.name] = [w]
                            elif w.total_time == category_records[t.name][0].total_time:
                                category_records[t.name] += w
                        else:
                            category_records[t.name] = [w]
        for t in team_categories:
            if t.name in category_records:
                for record in category_records[t.name]:
                    # Bug workaround, weird behaviour without this
                    try:
                        record.team_category
                    except Exception:
                        continue
                    # End bug workaround
                    team_records.append(
                        namedteamrecord(
                            record.team_category.name,
                            record.team_category.slug,
                            str(record.total_time),
                            record.winning_team,
                            record.event.date.year,
                            str(record.avg_time),
                            record.event.race.slug,
                        )
                    )
    hill_records = []
    if race.slug == "baden-road-races" and distance.slug == "7-mi":
        primeresults = Prime.objects.filter(
            event__race__slug=race.slug, event__distance__slug=distance.slug
        )
        results = Result.objects.filter(
            event__race__slug=race.slug, event__distance__slug=distance.slug
        )
        mptime = primeresults.filter(gender="M").order_by("time")[:1][0].time
        mptimes = primeresults.filter(gender="M", time=mptime)
        male_results = []
        for m in mptimes:
            result = results.get(event=m.event, place=m.place)
            male_results.append([m, result])
        for r in male_results:
            member = get_member(r[1], membership)
            hill_records.append(
                namedresult(
                    "Overall Male",
                    str(r[0].time).lstrip("0:"),
                    r[1].athlete,
                    r[1].event.date.year,
                    r[1].category.name,
                    r[1].city,
                    False,
                    r[1].event.race.slug,
                    member,
                )
            )
        fptime = primeresults.filter(gender="F").order_by("time")[:1][0].time
        fptimes = primeresults.filter(gender="F", time=fptime)
        female_results = []
        for f in fptimes:
            result = results.get(event=f.event, place=f.place)
            female_results.append([f, result])
        for r in female_results:
            member = get_member(r[1], membership)
            hill_records.append(
                namedresult(
                    "Overall Female",
                    str(r[0].time).lstrip("0:"),
                    r[1].athlete,
                    r[1].event.date.year,
                    r[1].category.name,
                    r[1].city,
                    False,
                    r[1].event.race.slug,
                    member,
                )
            )
    return records, team_records, hill_records


def makerecords(place, rtime, results, distance, membership):
    records = []
    for result in results:
        if distance.slug == "combined":
            member = get_member_endurrace(result, membership)
            records.append(
                namedresult(
                    place,
                    rtime,
                    result.athlete,
                    result.year,
                    result.category.name,
                    result.city,
                    False,
                    "endurrace",
                    member,
                )
            )
        else:
            member = get_member(result, membership)
            records.append(
                namedresult(
                    place,
                    rtime,
                    result.athlete,
                    result.event.date.year,
                    result.category.name,
                    result.city,
                    result.age,
                    result.event.race.slug,
                    member,
                )
            )
    return records


def create_samerace_list(race):
    """Make a list of races that are the same"""
    races = [race]
    for i in Samerace.objects.filter(current_race=race):
        races.append(i.old_race)
    for i in Samerace.objects.filter(old_race=race):
        races.append(i.current_race)
    return races


def get_membership(event=False, include_inactive=False):
    named_membership = namedtuple("nm", ["names", "includes", "excludes"])
    names = {}
    if include_inactive:
        members = Rwmember.objects.all()
    else:
        members = Rwmember.objects.filter(active=True)
    for m in members:
        names[m.name.lower()] = m
        if m.altname != "":
            names[m.altname.lower()] = m
    includes = {}
    dbinclude = Rwmembercorrection.objects.filter(correction_type="include")
    if event:
        dbinclude = dbinclude.filter(event=event)
    for i in dbinclude:
        includes["{}-{}".format(i.event.id, i.place)] = i.rwmember
    excludes = {}
    dbexclude = Rwmembercorrection.objects.filter(correction_type="exclude")
    if event:
        dbexclude = dbexclude.filter(event=event)
    for e in dbexclude:
        if e.place in excludes:
            excludes["{}-{}".format(e.event.id, e.place)] += e.rwmember
        else:
            excludes["{}-{}".format(e.event.id, e.place)] = [e.rwmember]
    membership = named_membership(names, includes, excludes)
    return membership


def get_member_dict():
    dbmembers = Rwmember.objects.filter(active=True)
    member_dict = {}
    for m in dbmembers:
        member_dict[m.name.lower()] = m
    for a in dbmembers:
        member_dict[a.altname.lower()] = a
    return member_dict


def get_member(result, membership):
    member = False
    lower_athlete = result.athlete.lower()
    if lower_athlete in membership.names:
        member = membership.names[lower_athlete]
    if "{}-{}".format(result.event.id, result.place) in membership.includes:
        member = membership.includes["{}-{}".format(result.event.id, result.place)]
    if member:
        if "{}-{}".format(result.event.id, result.place) in membership.excludes:
            if (
                member
                in membership.excludes["{}-{}".format(result.event.id, result.place)]
            ):
                member = False
    return member


def get_team_categories(event):
    present_team_categories = Teamresult.objects.filter(event=event).values_list(
        "team_category__name", flat=True
    )
    present_team_categories = set(sorted(present_team_categories))
    team_categories = Teamcategory.objects.filter(name__in=present_team_categories)
    return team_categories


def get_pages(
    event,
    page,
    team_categories,
    hill_dict=False,
    wheelchair_results=False,
    relay_dict=False,
):
    named_page = namedtuple("np", ("active", "href", "label"))
    pages = []
    if page == "Overall":
        pages.append(named_page("active", "#", "Overall"))
    else:
        pages.append(
            named_page(
                "inactive",
                "/event/{}/{}/{}/".format(
                    event.date.year, event.race.slug, event.distance.slug
                ),
                "Overall",
            )
        )
    if relay_dict:
        if page == "Relay":
            pages.append(named_page("active", "#", "Relay"))
        else:
            pages.append(
                named_page(
                    "inactive",
                    "/relay/{}/{}/{}/".format(
                        event.date.year, event.race.slug, event.distance.slug
                    ),
                    "Relay",
                )
            )

    if hill_dict:
        if page == "Hill Sprint":
            pages.append(named_page("active", "#", "Hill Sprint"))
        else:
            pages.append(
                named_page(
                    "inactive",
                    "/event/{}/{}/{}/?hill=true".format(
                        event.date.year, event.race.slug, event.distance.slug
                    ),
                    "Hill Sprint",
                )
            )
    if wheelchair_results:
        if page == "Wheelchair":
            pages.append(named_page("active", "#", "Wheelchair"))
        else:
            pages.append(
                named_page(
                    "inactive",
                    "/event/{}/{}/{}/?wheelchair=true".format(
                        event.date.year, event.race.slug, event.distance.slug
                    ),
                    "Wheelchair",
                )
            )
    for tc in team_categories:
        pages.append(
            named_page(
                "inactive",
                "/event/{}/{}/{}/team/{}".format(
                    event.date.year, event.race.slug, event.distance.slug, tc.slug
                ),
                tc.name,
            )
        )
    return pages


def get_relay_records(year=None):
    """Get records for Loop relay"""
    events = Relay.objects.order_by().values_list("event").distinct()
    if year:
        events = events.filter(event__date__year=year)
    individual_results_dict = get_individual_results_dict(events)
    relay_results = get_relay_results(events)
    team_results = get_team_results(relay_results, individual_results_dict)
    categories = ValidRelayCategories().categories
    relay_records = {}
    for c in categories.values():
        relay_records[c] = []
    for i in team_results:
        for j in i.categories:
            if relay_records[j] == []:
                relay_records[j] = [i]
            elif i.team_time < relay_records[j][0].team_time:
                relay_records[j] = [i]
            elif i.team_time == relay_records[j][0].team_time:
                relay_records[j].append(i)
    return relay_records

def get_config_value_or_false(name):
    try:
        value = Config.objects.get(name=name).value
    except:
        value = False
    else:
        if value == "":
            value = False
    return value

def get_race_by_slug_or_false(slug):
    try:
        race = Race.objects.get(slug=slug)
    except:
        race = False
    return race

def get_distance_by_slug_or_false(slug):
    try:
        distance = Distance.objects.get(slug=slug)
    except:
        distance = False
    return distance

