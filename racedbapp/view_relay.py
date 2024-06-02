from collections import namedtuple
from operator import attrgetter
from urllib import parse

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from django.http import Http404
from django.shortcuts import render

from racedbapp.shared.types import Choice, Filter

from .shared import shared
from .config import ValidRelayCategories
from .models import Event, Relay, Result, Teamcategory, Teamresult

valid_categories = ValidRelayCategories().categories


def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    category = False
    if "category" in qstring:
        category = qstring["category"][0]
    events = get_events(year, race_slug, distance_slug)
    individual_results_dict = get_individual_results_dict(events)
    relay_results = get_relay_results(events)
    max_leg = relay_results.aggregate(Max("relay_leg"))["relay_leg__max"]
    team_results = get_team_results(relay_results, individual_results_dict)
    team_results = sorted(team_results, key=attrgetter("team_time", "place"))
    team_categories = local_get_team_categories(events)
    pages = []
    filters = {
        "year_filter": get_year_filter(events[0]),
        "category_filter": get_category_filter(events[0], category, team_results, year),
    }
    if category:
        team_results = [
            x for x in team_results if valid_categories[category] in x.categories
        ]
    if year != "all":
        pages = shared.get_pages(
            events[0], "Relay", team_categories, relay_dict=True
        )
    context = {
        "event": EventV(events[0], max_leg),
        "pages": pages,
        "filters": filters,
        "team_results": team_results,
        "year": year,
    }
    return render(request, "racedbapp/relay.html", context)


def local_get_team_categories(events):
    present_team_categories = Teamresult.objects.filter(event__in=events).values_list(
        "team_category__name", flat=True
    )
    present_team_categories = set(sorted(present_team_categories))
    team_categories = Teamcategory.objects.filter(name__in=present_team_categories)
    return team_categories


def get_events(year, race_slug, distance_slug):
    """Get the events based on query parameters or return 404"""
    events = Event.objects.select_related().filter(
        race__slug=race_slug, distance__slug=distance_slug
    )
    if year == "all":
        events = events.filter(date__gte="2018-01-01")
    else:
        events = events.filter(date__icontains=year)
    if not events:
        raise Http404("Event not found")
    return events


def get_individual_results_dict(events):
    individual_results_dict = {}
    individual_results = Result.objects.select_related().filter(event__in=events)
    for i in individual_results:
        yearplace = "{}-{}".format(i.event.date.year, i.place)
        individual_results_dict[yearplace] = i
    return individual_results_dict


def get_relay_results(events):
    relay_results = Relay.objects.filter(event__in=events)
    if len(relay_results) == 0:
        raise Http404("No results found")
    return relay_results


def get_year_filter(event):
    rawresults = Relay.objects.select_related().filter(event__race=event.race)
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
        choices.append(
            Choice(
                year, "/relay/{}/{}/{}/".format(year, d[1], event.distance.slug)
            )
        )
    year_filter = Filter(event.date.year, choices)
    return year_filter


def get_category_filter(event, category, team_results, year):
    choices = []
    if year == "all":
        event_date_year = "all"
    else:
        event_date_year = event.date.year
    if category:
        if category not in valid_categories:
            raise Http404("No results found")
        full_category = valid_categories[category]
        choices.append(
            Choice(
                "All",
                "/relay/{}/{}/{}/".format(
                    event_date_year, event.race.slug, event.distance.slug
                ),
            )
        )
    else:
        full_category = "All"
    present_categories = []
    for i in team_results:
        present_categories += i.categories
    present_categories = set(present_categories)
    for k, v in valid_categories.items():
        if v in present_categories and k != category:
            choices.append(
                Choice(
                    v,
                    "/relay/{}/{}/{}/?category={}".format(
                        event_date_year, event.race.slug, event.distance.slug, k
                    ),
                )
            )
    category_filter = Filter(full_category, choices)
    return category_filter


def get_team_results(relay_results, individual_results_dict):
    team_results = []
    teams_dict = {}
    for i in relay_results:
        teamyearplace = "{}-{}".format(i.relay_team_place, i.event.date.year)
        if teamyearplace not in teams_dict:
            teams_dict[teamyearplace] = RelayResult(i)
        individualyearplace = "{}-{}".format(i.event.date.year, i.place)
        leg = RelayLeg(i, individual_results_dict[individualyearplace])
        teams_dict[teamyearplace].legs.append(leg)
    for _k, v in teams_dict.items():
        v.calc_categories()
        v.legs = sorted(v.legs, key=attrgetter("leg"))
        team_results.append(v)
    return team_results


class EventV:
    def __init__(self, event, max_leg):
        self.city = event.city
        self.date = event.date
        self.flickrsetid = event.flickrsetid
        self.youtube_id = event.youtube_id
        self.distance_name = event.distance.name
        self.relay_leg_distance = event.distance.km
        self.total_relay_distance = event.distance.km * max_leg
        self.race_name = event.race.name
        self.race_shortname = event.race.shortname
        self.race_slug = event.race.slug


class RelayResult:
    def __init__(self, relay_result):
        self.place = relay_result.relay_team_place
        self.team = relay_result.relay_team
        self.team_id = relay_result.id
        self.team_time = relay_result.relay_team_time
        self.team_place = relay_result.relay_team_place
        self.legs = []
        self.categories = []
        self.year = relay_result.event.date.year

    def calc_categories(self):
        self.genders = list({x.gender for x in self.legs})
        if len(self.genders) > 1:
            self.gender = "Mixed"
            self.categories.append("Mixed")
        elif self.genders == ["F"]:
            self.gender = "Female"
            self.categories.append("Female")
        elif self.genders == ["M"]:
            self.gender = "Male"
            self.categories.append("Male")
        if all([x.ismasters for x in self.legs]):
            self.ismasters = True
            if "Female" in self.categories:
                self.categories.append("Female Masters")
            elif "Male" in self.categories:
                self.categories.append("Male Masters")
            elif "Mixed" in self.categories:
                self.categories.append("Mixed Masters")
        else:
            self.ismasters = False

    def __repr__(self):
        return "RelayResult(place={}, year={}, team={})".format(
            self.place, self.year, self.team
        )


class RelayLeg:
    def __init__(self, relay_result, individual_result):
        self.leg = relay_result.relay_leg
        self.athlete = individual_result.athlete
        self.gender = individual_result.gender
        self.category = individual_result.category.name
        self.ismasters = individual_result.category.ismasters
        if individual_result.rwmember:
            if individual_result.rwmember.active:
                self.member_slug = individual_result.rwmember.slug
        else:
            self.member_slug = False
        self.guntime = individual_result.guntime
        self.city = individual_result.city

    def __repr__(self):
        return "RelayLeg(Leg={}, athlete={})".format(self.leg, self.athlete)
