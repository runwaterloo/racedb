from collections import OrderedDict, defaultdict
from datetime import datetime
from operator import attrgetter
from urllib import parse

from django.db.models import Count
from django.http import Http404
from django.shortcuts import redirect, render

from racedbapp.shared.types import Choice, Filter

from .models import Config, Event, Result, Rwmember, Rwmembertag


def index(request, year, leaderboard_only=False, standings_only=False):
    config_values = (
        "boost_classic_points",
        "boost_ditto_points",
        "boost_leaderboard_size",
        "boost_max_endurrun",
        "boost_max_events",
        "boost_merit_max",
        "boost_participation_points",
        "boost_pb_points",
        "nophoto_url",
    )
    config_dict = dict(Config.objects.values_list("name", "value").filter(name__in=config_values))
    max_events = int(config_dict.get("boost_max_events", 0))
    max_endurrun = int(config_dict.get("boost_max_endurrun", 0))
    leaderboard_size = int(config_dict.get("boost_leaderboard_size", 0))
    nophoto_url = config_dict.get("nophoto_url", "")
    boost_years = get_boost_years()
    if not boost_years:
        return render(request, "racedbapp/boost.html")
    if year == "latest":
        return redirect("/boost/{}/".format(boost_years[0]))
    else:
        year = int(year)
    first_day = datetime(year, 1, 1).date()
    last_day = datetime(year, 12, 31).date()
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    qs_filter = get_qs_filter(qstring)
    qs_date = ""
    if "date" in qstring:
        try:
            ymd = [int(x) for x in qstring["date"][0].split("-")]
            qs_date = datetime(*ymd).date()
        except Exception:
            raise Http404("Invalid date")
        else:
            if first_day <= qs_date <= last_day:
                last_day = qs_date
            else:
                raise Http404("Invalid date")
    gender_finishers = get_gender_finishers(first_day, last_day)
    boost_tag = get_boost_tag(year)
    included_members = Rwmember.objects.filter(
        year_of_birth__isnull=False,
        tags=boost_tag,
        gender__in=["M", "F"],
    )
    qs_member = get_qs_member(qstring, included_members)
    previous_races = get_previous_races(year, included_members)
    battlers = {}
    for i in included_members:
        battlers[i.id] = Battler(i, year, nophoto_url)
    dbresults = (
        Result.objects.select_related()
        .filter(
            event__date__range=(first_day, last_day),
            gender_place__isnull=False,
            rwmember__in=included_members,
        )
        .order_by("event__date")
    )
    for i in dbresults:
        battlers[i.rwmember_id].results.append(
            BResult(i, gender_finishers, config_dict, previous_races)
        )
    for v in battlers.values():
        v.calculate(max_events, max_endurrun)
    gender_place_dict = {"F": 0, "M": 0, "NB": 0}
    category_place_dict = {}
    leaders = {"F40-": [], "M40-": [], "F40+": [], "M40+": [], "NB40-": [], "NB40+": []}
    standings = []
    count = 1
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
        if qs_filter != "":
            if qs_filter in ("F", "M"):
                if i.gender != qs_filter:
                    continue
            else:
                if i.category != qs_filter:
                    continue
        standings.append(i)
        if qs_member:
            if i.member_id == qs_member.id:
                member_results = i
    if standings_only:
        return standings
    leaderboard = OrderedDict()
    leaderboard["Female Under 40"] = leaders["F40-"]
    leaderboard["Male Under 40"] = leaders["M40-"]
    leaderboard["Female Over 40"] = leaders["F40+"]
    leaderboard["Male Over 40"] = leaders["M40+"]
    if leaderboard_only:
        return leaderboard
    standings_filter = get_standings_filter(qs_filter, qs_date, year)
    date_filter = get_date_filter(qs_date, year)
    if qs_member:
        context = {
            "config_dict": config_dict,
            "qs_member": qs_member,
            "member_results": member_results,
            "year": year,
        }
        return render(request, "racedbapp/boost_member.html", context)
    else:
        context = {
            "leaderboard": leaderboard,
            "standings": standings,
            "standings_filter": standings_filter,
            "date_filter": date_filter,
            "qs_date": qs_date,
            "year": year,
            "boost_years": boost_years,
        }
        return render(request, "racedbapp/boost.html", context)


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
        .annotate(num_events=Count("result"))
        .filter(num_events__gte=1)
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
    results = Result.objects.select_related().filter(
        event__date__range=(first_day, last_day), rwmember_id__in=included_members
    )
    for i in results:
        if i.rwmember_id in previous_races:
            previous_races[i.rwmember_id].append(i.event.race)
        else:
            previous_races[i.rwmember_id] = [i.event.race]
    return previous_races


def get_gender_finishers(first_day, last_day):
    gender_finishers = {}
    for i in ("F", "M"):
        db = (
            Event.objects.values("id")
            .filter(
                date__range=(first_day, last_day),
                result__gender=i,
                result__place__lt=990000,
            )
            .annotate(num_finishers=Count("result"))
        )
        thisdict = {}
        for j in db:
            thisdict[j["id"]] = j["num_finishers"]
        gender_finishers[i] = thisdict
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

    def calculate(self, max_events, max_endurrun):
        self.results = sorted(self.results, key=attrgetter("ep"), reverse=True)
        events_count = endurrun_count = 0
        for i in self.results:
            if events_count == max_events:
                break
            else:
                if "endurrun" in i.event_race_slug:
                    if endurrun_count == max_endurrun:
                        continue
                    else:
                        endurrun_count += 1
                events_count += 1
                i.counts = True
                self.total_points += i.ep
        self.results = sorted(self.results, key=attrgetter("counts", "ep"), reverse=True)


class BResult:
    def __init__(self, result, gender_finishers, config_dict, previous_races):
        self.event_id = result.event.id
        self.event_race_short_name = result.event.race.shortname
        self.event_race_slug = result.event.race.slug
        self.event_distance_name = result.event.distance.name
        self.event_distance_slug = result.event.distance.slug
        self.guntime = result.guntime
        self.gender_place = result.gender_place
        self.gender_finishers = gender_finishers[result.gender][result.event.id]
        self.mp = (1 - (self.gender_place / self.gender_finishers)) * int(
            config_dict["boost_merit_max"]
        )
        self.ditto_boost = self.pb_boost = self.classic_boost = 0
        if result.rwmember_id in previous_races:
            if result.event.race in previous_races[result.rwmember_id]:
                self.ditto_boost = int(config_dict["boost_ditto_points"])
        if result.isrwpb:
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
