from django.shortcuts import render
from django.http import HttpResponse, Http404
from collections import namedtuple
from operator import attrgetter
from datetime import datetime
from random import randint
from urllib import parse

from .models import *

BowResult = namedtuple('bowresult', ['athlete',
                                     'slug',
                                     'gender',
                                     'gender_place',
                                     'category',
                                     'category_place',
                                     'photourl',
                                     'participation_points',
                                     'performance_points',
                                     'volunteer_points',
                                     'total_points',
                                     'city'])

named_filter = namedtuple('nf', ['current', 'choices'])
named_choice = namedtuple('nc', ['name', 'url'])

def index(request, year):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    qs_filter = get_qs_filter(qstring)
    female_under_40 = []
    female_over_40 = []
    male_under_40 = []
    male_over_40 = []
    standings1 = []
    gender_place_dict = {}
    category_place_dict = {}
    #bow_tag = Rwmembertag.objects.get(name='bow-2017')
    #bow_members = Rwmember.objects.filter(tags=bow_tag).order_by('id')
    bow_members = Rwmember.objects.filter(active=True)
    gender_finishers = get_gender_finishers()
    for member in bow_members:
        if not member.year_of_birth:
            continue
        age = 2017 - member.year_of_birth
        if age < 40:
            if member.gender == 'F':
                category = 'F40-'
            else:
                category = 'M40-'
        else:
            if member.gender == 'F':
                category = 'F40+'
            else:
                category = 'M40+'
        slug = None
        if member.active:
            slug = member.slug
        if member.photourl:
            photourl = member.photourl
        else:
            if member.gender == 'F':
                photourl = 'http://www.supercoloring.com/sites/default/files/silhouettes/2015/05/jogger-grey-silhouette.svg'
            else:
                photourl = 'http://www.supercoloring.com/sites/default/files/silhouettes/2015/05/jogging-grey-silhouette.svg'
        results = Result.objects.filter(event__date__contains='2017', rwmember=member)
        pointslist = []
        for r in results:
            if not r.gender_place:
                continue
            perf = 0
            participation = 100
            merit = (1 - (r.gender_place / gender_finishers[r.gender][r.event.id]))*50 
            perf += merit
            if 'classic' in r.event.race.slug:
                perf = perf * 2
                participation = participation * 2
            pointslist.append([participation + perf, participation, perf])
        pointslist = sorted(pointslist, reverse=True)[0:10]
        participation_points = 0
        performance_points = 0
        for i in pointslist:
            participation_points += i[1]
            performance_points += i[2]
        volunteer_points = 0
        total_points = round(participation_points + performance_points + volunteer_points)
        if total_points == 0:
            continue
        #category = '{}{}-{}'.format(member.gender, age - age % 40, (age - age % 10) + 9)
        standings1.append(BowResult(member.name,
                                   slug,
                                   member.gender,
                                   0,
                                   category,  
                                   0, 
                                   photourl,
                                   participation_points,
                                   round(performance_points),
                                   volunteer_points,
                                   total_points,
                                   member.city))

    standings2 = []
    for member in sorted(standings1, key=attrgetter('total_points'), reverse=True):
        if member.gender in gender_place_dict:
            gender_place_dict[member.gender] += 1
        else:
            gender_place_dict[member.gender] = 1
        if member.category in category_place_dict:
            category_place_dict[member.category] += 1
        else:
            category_place_dict[member.category] = 1
        standings2.append(BowResult(member.athlete,
                                    member.slug,
                                    member.gender,
                                    gender_place_dict[member.gender],
                                    member.category,  
                                    category_place_dict[member.category],
                                    member.photourl,
                                    member.participation_points,
                                    member.performance_points,
                                    member.volunteer_points,
                                    member.total_points,
                                    member.city))
    for member in standings2:
        if member.category == 'F40-':
            female_under_40.append(BowResult(member.athlete,
                                             member.slug,
                                             member.gender,
                                             member.gender_place,
                                             member.category,
                                             member.category_place,
                                             member.photourl,
                                             member.participation_points,
                                             member.performance_points,
                                             member.volunteer_points,
                                             member.total_points,
                                             member.city))
        elif member.category == 'F40+':
            female_over_40.append(BowResult(member.athlete,
                                            member.slug,
                                            member.gender,
                                            member.gender_place,
                                            member.category,
                                            member.category_place,
                                            member.photourl,
                                            member.participation_points,
                                            member.performance_points,
                                            member.volunteer_points,
                                            member.total_points,
                                            member.city))
        elif member.category == 'M40-':
            male_under_40.append(BowResult(member.athlete,
                                           member.slug,
                                           member.gender,
                                           member.gender_place,
                                           member.category,
                                           member.category_place,
                                           member.photourl,
                                           member.participation_points,
                                           member.performance_points,
                                           member.volunteer_points,
                                           member.total_points,
                                           member.city))
        elif member.category == 'M40+':
            male_over_40.append(BowResult(member.athlete,
                                          member.slug,
                                          member.gender,
                                          member.gender_place,
                                          member.category,
                                          member.category_place,
                                          member.photourl,
                                          member.participation_points,
                                          member.performance_points,
                                          member.volunteer_points,
                                          member.total_points,
                                          member.city))


    standings3 = [x for x in standings2 if qs_filter in x.category]
    standings_filter = get_standings_filter(qs_filter)
    context = {
               'female_under_40': female_under_40[0:5],
               'female_over_40': female_over_40[0:5],
               'male_under_40': male_under_40[0:5],
               'male_over_40': male_over_40[0:5],
               'standings': standings3,
               'standings_filter': standings_filter,
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

def get_standings_filter(qs_filter):
    choices = []
    choices.append(named_choice('', '/newthing'))
    choices.append(named_choice('Female', '/newthing/?filter=F'))
    choices.append(named_choice('Male', '/newthing/?filter=M'))
    choices.append(named_choice('F40-', '/newthing/?filter=F40-'))
    choices.append(named_choice('M40-', '/newthing/?filter=M40-'))
    choices.append(named_choice('F40+', '/newthing/?filter=F40%2B'))
    choices.append(named_choice('M40+', '/newthing/?filter=M40%2B'))
    choices = [x for x in choices if x[0] != qs_filter]
    if  qs_filter == 'F':
        current_choice = 'Female'
    elif qs_filter == 'M':
        current_choice = 'Male'
    elif qs_filter == '':
        current_choice = ''
    else:
        current_choice = qs_filter
    standings_filter = named_filter(current_choice, choices)
    return standings_filter

def get_gender_finishers():
    gender_finishers = {}
    for i in ('F', 'M'):
        db = (Event.objects.values('id')
              .filter(date__contains='2017',
                      result__gender=i,
                      result__place__lt=990000)
              .annotate(num_finishers=Count('result')))
        thisdict = {}
        for j in db:
            thisdict[j['id']] = j['num_finishers']
        gender_finishers[i] = thisdict
    return gender_finishers
