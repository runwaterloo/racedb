from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render
from collections import namedtuple
from operator import attrgetter
from urllib import parse
from . import view_shared
from .models import (
    Event,
    Relay,
    Result,
    )

named_filter = namedtuple('nf', ['current', 'choices'])
named_choice = namedtuple('nc', ['name', 'url'])

valid_categories = {
    'female': 'Female',
    'male': 'Male',
    'mixed': 'Mixed',
    'masters': 'Masters',
    'female-masters': 'Female Masters',
    'male-masters': 'Male Masters',
    'mixed-masters': 'Mixed Masters',
    }


def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    category = False
    if 'category' in qstring:
        category = qstring['category'][0]
    event = get_event(year, race_slug, distance_slug)
    individual_results_dict = get_individual_results_dict(event)
    relay_results = get_relay_results(event)
    team_results = get_team_results(relay_results, individual_results_dict)
    team_categories = view_shared.get_team_categories(event)
    pages = view_shared.get_pages(
        event,
        'Relay',
        team_categories,
        laurier_relay_dict=True,
        )
    filters = {
        'year_filter': get_year_filter(event),
        'category_filter': get_category_filter(event, category, team_results),
    }
    if category:
        team_results = [
            x for x in team_results
            if valid_categories[category]
            in x.categories
            ]
    context = {
        'event': EventV(event),
        'pages': pages,
        'filters': filters,
        'team_results': team_results,
        }
    return render(request, 'racedbapp/relay.html', context)


def get_event(year, race_slug, distance_slug):
    """ Get the event based on query parameters or return 404 """
    try:
        event = Event.objects.select_related().get(
            race__slug=race_slug,
            distance__slug=distance_slug,
            date__icontains=year
            )
    except ObjectDoesNotExist:
        raise Http404('Event not found')
    return event


def get_individual_results_dict(event):
    individual_results_dict = {}
    individual_results = Result.objects.select_related().filter(event=event)
    for i in individual_results:
        individual_results_dict[i.place] = i
    return individual_results_dict


def get_relay_results(event):
    relay_results = Relay.objects.filter(
        event=event).order_by('relay_team_place')
    if len(relay_results) == 0:
        raise Http404('No results found')
    return relay_results


def get_year_filter(event):
    rawresults = Relay.objects.select_related().filter(event__race=event.race)
    dates = (rawresults
             .order_by('-event__date')
             .values_list('event__date', 'event__race__slug')
             .distinct())
    choices = []
    for d in dates:
        year = d[0].year
        if year == event.date.year:
            continue
        choices.append(named_choice(year, '/relay/{}/{}/{}/'.format(
            year, d[1], event.distance.slug)))
    year_filter = named_filter(event.date.year, choices)
    return year_filter


def get_category_filter(event, category, team_results):
    choices = []
    if category:
        if category not in valid_categories:
            raise Http404('No results found')
        full_category = valid_categories[category]
        choices.append(named_choice('All', '/relay/{}/{}/{}/'.format(
            event.date.year, event.race.slug, event.distance.slug)))
    else:
        full_category = 'All'
    present_categories = []
    for i in team_results:
        present_categories += i.categories
    present_categories = set(present_categories)
    for k, v in valid_categories.items():
        if v in present_categories and k != category:
            choices.append(named_choice(
                v, '/relay/{}/{}/{}/?category={}'.format(
                    event.date.year,
                    event.race.slug,
                    event.distance.slug,
                    k,
                    )
                ))
    category_filter = named_filter(full_category, choices)
    return category_filter


def get_team_results(relay_results, individual_results_dict):
    team_results = []
    teams_dict = {}
    for i in relay_results:
        if i.relay_team_place not in teams_dict:
            teams_dict[i.relay_team_place] = RelayResult(i)
        leg = RelayLeg(i, individual_results_dict[i.place])
        teams_dict[i.relay_team_place].legs.append(leg)
    for k, v in teams_dict.items():
        v.calc_categories()
        v.legs = sorted(v.legs, key=attrgetter('leg'))
        team_results.append(v)
    team_results = sorted(team_results, key=attrgetter('place'))
    return team_results


class EventV:
    def __init__(self, event):
        self.city = event.city
        self.date = event.date
        self.flickrsetid = event.flickrsetid
        self.youtube_id = event.youtube_id
        self.distance_name = event.distance.name
        self.relay_leg_distance = event.distance.km
        self.total_relay_distance = event.distance.km * 4
        self.race_name = event.race.name
        self.race_shortname = event.race.shortname
        self.race_slug = event.race.slug


class RelayResult:
    def __init__(self, relay_result):
        self.place = relay_result.relay_team_place
        self.team = relay_result.relay_team
        self.team_id = relay_result.id
        self.team_time = relay_result.relay_team_time
        self.legs = []
        self.categories = []

    def calc_categories(self):
        self.genders = list(set([x.gender for x in self.legs]))
        if len(self.genders) > 1:
            self.gender = 'Mixed'
            self.categories.append('Mixed')
        elif self.genders == ['F', ]:
            self.gender = 'Female'
            self.categories.append('Female')
        elif self.genders == ['M', ]:
            self.gender = 'Male'
            self.categories.append('Male')
        if all([x.ismasters for x in self.legs]):
            self.ismasters = True
            self.categories.append('Masters')
            if 'Female' in self.categories:
                self.categories.append('Female Masters')
            elif 'Male' in self.categories:
                self.categories.append('Male Masters')
            elif 'Mixed' in self.categories:
                self.categories.append('Mixed Masters')
        else:
            self.ismasters = False

    def __repr__(self):
        return 'RelayResult(place={}, team={})'.format(self.place, self.team)


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
        return 'RelayLeg(Leg={}, athlete={})'.format(self.leg, self.athlete)
