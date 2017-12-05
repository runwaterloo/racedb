from django.shortcuts import render
from django.db.models import Count
from django.http import Http404
from collections import namedtuple, OrderedDict
from datetime import datetime
from operator import attrgetter
from urllib import parse

from .models import (
    Config,
    Event,
    Result,
    Rwmember
)


def index(request, year):
    config_dict = dict(Config.objects.values_list('name', 'value'))
    max_events = int(config_dict['newthing_max_events'])
    leaderboard_size = int(config_dict['newthing_leaderboard_size'])
    classic_multiplier = float(config_dict['newthing_classic_multiplier'])
    participation_default = int(config_dict['newthing_participation_default'])
    merit_max = int(config_dict['newthing_merit_max'])
    year = int(year)
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    qs_filter = get_qs_filter(qstring)
    first_day = datetime(year, 1, 1).date()
    last_day = datetime(year, 12, 31).date()
    gender_finishers = get_gender_finishers(first_day, last_day)
    included_members = Rwmember.objects.filter(active=True)
    qs_member = get_qs_member(qstring, included_members)
    battlers = {}
    for i in included_members:
        battlers[i.id] = Battler(i, year)
    dbresults = Result.objects.select_related().filter(
                  event__date__range=(first_day, last_day),
                  gender_place__isnull=False,
                  rwmember__in=included_members).order_by('event__date')
    for i in dbresults:
        battlers[i.rwmember_id].results.append(BResult(i, gender_finishers, classic_multiplier, participation_default, merit_max))
    for v in battlers.values():
        v.calculate(max_events)
    gender_place_dict = {'F': 0, 'M': 0}
    category_place_dict = {}
    leaders = {'F40-': [],
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
        if len(leaders[i.category]) < leaderboard_size:
            leaders[i.category].append(i)
        if qs_filter != '':
            if qs_filter in ('F', 'M'):
                if i.gender != qs_filter:
                    continue
            else:
                if i.category != qs_filter:
                    continue
        standings.append(i)
        if qs_member:
            if i.member_id == qs_member.id:
                member_results = i
    leaderboard = OrderedDict()
    leaderboard['Female Under 40'] = leaders['F40-']
    leaderboard['Male Under 40'] = leaders['M40-']
    leaderboard['Female Over 40'] = leaders['F40+']
    leaderboard['Male Over 40'] = leaders['M40+']
    standings_filter = get_standings_filter(qs_filter, year)
    if qs_member:
        context = {
                   'qs_member': qs_member,
                   'member_results': member_results,
                   'year': year
                  }
        return render(request, 'racedbapp/newthing_member.html', context)
    else:
        context = {
                   'leaderboard': leaderboard,
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

def get_qs_member(qstring, included_members):
    member = False
    if 'member' in qstring:
        members = included_members.filter(slug=qstring['member'][0])
        if len(members) == 1:
            member = members[0]
        else:
            raise Http404('Member not found')
    return member



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

    def calculate(self, max_events):
        self.results = sorted(
            self.results,
            key=attrgetter('ep'),
            reverse=True)
        self.x_best_results = self.results[0:max_events]
        for i in self.x_best_results:
            self.participation_points += i.pp
            self.merit_points += i.mp
            i.counts = True
        self.total_points = (self.participation_points
                             + self.merit_points
                             + self.volunteer_points)


class BResult:
    def __init__(self, result, gender_finishers, classic_multiplier, participation_default, merit_max):
        self.event_id = result.event.id
        self.event_race_name = result.event.race.name
        self.event_distance_name = result.event.distance.name
        self.gender_place = result.gender_place
        self.pp = participation_default
        self.mp = ((1 - (self.gender_place
                   / gender_finishers[result.gender][result.event.id]))
                   * merit_max)
        self.classic = False
        self.boost = 1.0
        if 'classic' in result.event.race.slug:
            self.classic = True
            self.boost = classic_multiplier
            self.pp = self.pp * classic_multiplier
            self.mp = self.mp * classic_multiplier
        self.ep = self.pp + self.mp
        self.counts = False
