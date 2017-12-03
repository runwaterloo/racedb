from django.shortcuts import render
from django.db.models import Count
from django.http import Http404
from collections import namedtuple
from datetime import datetime
from operator import attrgetter
from urllib import parse

from .models import (
    Event,
    Result,
    Rwmember
)

max_events = 10
leaderboard_size = 5
classic_multiplier = 2
participation_default = 100
merit_default = 50


def index(request, year):
    year = int(year)
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    qs_filter = get_qs_filter(qstring)
    first_day = datetime(year, 1, 1).date()
    last_day = datetime(year, 12, 31).date()
    gender_finishers = get_gender_finishers(first_day, last_day)
    included_members = Rwmember.objects.filter(active=True)
    battlers = {}
    for i in included_members:
        battlers[i.id] = Battler(i, year)
    dbresults = Result.objects.select_related().filter(
                  event__date__range=(first_day, last_day),
                  gender_place__isnull=False,
                  rwmember__in=included_members)
    for i in dbresults:
        battlers[i.rwmember_id].results.append(BResult(i, gender_finishers))
    for v in battlers.values():
        v.calculate()
    gender_place_dict = {'F': 0, 'M': 0}
    category_place_dict = {}
    leaderboard = {'F40-': [],
                   'M40-': [],
                   'F40+': [],
                   'M40+': []}
    standings = []
    for i in sorted(battlers.values(),
                    key=attrgetter('total_points'),
                    reverse=True):
        if i.total_points == 0:
            continue
        gender_place_dict[i.gender] += 1
        i.gender_place = gender_place_dict[i.gender]
        if i.category in category_place_dict:
            category_place_dict[i.category] += 1
            i.category_place = category_place_dict[i.category]
        else:
            i.category_place = category_place_dict[i.category] = 1
        if len(leaderboard[i.category]) < leaderboard_size:
            leaderboard[i.category].append(i)
        if qs_filter != '':
            if qs_filter in ('F', 'M'):
                if i.gender != qs_filter:
                    continue
            else:
                if i.category != qs_filter:
                    continue
        standings.append(i)
    female_under_40 = leaderboard['F40-']
    male_under_40 = leaderboard['M40-']
    female_over_40 = leaderboard['F40+']
    male_over_40 = leaderboard['M40+']
    standings_filter = get_standings_filter(qs_filter, year)
    context = {
               'female_under_40': female_under_40,
               'female_over_40': female_over_40,
               'male_under_40': male_under_40,
               'male_over_40': male_over_40,
               'standings': standings,
               'standings_filter': standings_filter,
               'year': year
              }
    return render(request, 'racedbapp/newthing.html', context)


def get_qs_filter(qstring):
    valid_filters = ('F', 'M', 'F40-', 'F40+', 'M40-', 'M40+')
    qs_filter = ''
    if 'filter' in qstring:
        raw_filter = qstring['filter'][0]
        if raw_filter in valid_filters:
            qs_filter = raw_filter
        else:
            raise Http404('Filter not found')
    return qs_filter


def get_standings_filter(qs_filter, year):
    named_filter = namedtuple('nf', ['current', 'choices'])
    named_choice = namedtuple('nc', ['name', 'url'])
    choices = []
    choices.append(named_choice('', '/newthing/{}'.format(year)))
    choices.append(
        named_choice('Female', '/newthing/{}/?filter=F'.format(year)))
    choices.append(
        named_choice('Male', '/newthing/{}/?filter=M'.format(year)))
    choices.append(
        named_choice('F40-', '/newthing/{}/?filter=F40-'.format(year)))
    choices.append(
        named_choice('M40-', '/newthing/{}/?filter=M40-'.format(year)))
    choices.append(
        named_choice('F40+', '/newthing/{}/?filter=F40%2B'.format(year)))
    choices.append(
        named_choice('M40+', '/newthing/{}/?filter=M40%2B'.format(year)))
    choices = [x for x in choices if x[0] != qs_filter]
    if qs_filter == 'F':
        current_choice = 'Female'
    elif qs_filter == 'M':
        current_choice = 'Male'
    elif qs_filter == '':
        current_choice = ''
    else:
        current_choice = qs_filter
    standings_filter = named_filter(current_choice, choices)
    return standings_filter


def get_gender_finishers(first_day, last_day):
    gender_finishers = {}
    for i in ('F', 'M'):
        db = (Event.objects.values('id')
              .filter(date__range=(first_day, last_day),
                      result__gender=i,
                      result__place__lt=990000)
              .annotate(num_finishers=Count('result')))
        thisdict = {}
        for j in db:
            thisdict[j['id']] = j['num_finishers']
        gender_finishers[i] = thisdict
    return gender_finishers


class Battler:
    def __init__(self, member, year):
        self.member_id = member.id
        self.athlete = member.name
        self.slug = member.slug
        self.gender = member.gender
        self.age = year - member.year_of_birth
        if member.photourl:
            self.photourl = member.photourl
        else:
            if self.gender == 'F':
                self.photourl = 'http://www.supercoloring.com/sites/default/files/silhouettes/2015/05/jogger-grey-silhouette.svg'
            else:
                self.photourl = 'http://www.supercoloring.com/sites/default/files/silhouettes/2015/05/jogging-grey-silhouette.svg'
        self.ismaster = False
        self.category_suffix = '40-'
        if self.age >= 40:
            self.ismaster = True
            self.category_suffix = '40+'
        self.category = self.gender + self.category_suffix
        self.city = member.city
        self.results = []
        self.x_best_results = []
        self.participation_points = 0
        self.merit_points = 0
        self.volunteer_points = 0
        self.total_points = 0
        self.gender_place = 0
        self.category_place = 0

    def calculate(self):
        self.x_best_results = sorted(
            self.results,
            key=attrgetter('ep'),
            reverse=True)[0:max_events]
        for i in self.x_best_results:
            self.participation_points += i.pp
            self.merit_points += i.mp
            i.counts = True
        self.total_points = (self.participation_points
                             + self.merit_points
                             + self.volunteer_points)


class BResult:
    def __init__(self, result, gender_finishers):
        self.event_id = result.event.id
        self.event_race_name = result.event.race.name
        self.event_distance_name = result.event.distance.name
        self.gender_place = result.gender_place
        self.pp = participation_default
        self.mp = ((1 - (self.gender_place
                   / gender_finishers[result.gender][result.event.id]))
                   * merit_default)
        if 'classic' in result.event.race.slug:
            self.pp = self.pp * classic_multiplier
            self.mp = self.mp * classic_multiplier
        self.ep = self.pp + self.mp
        self.counts = False
