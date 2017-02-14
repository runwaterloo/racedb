from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Min, Count, Sum, Avg
from django import db
from collections import namedtuple
from datetime import timedelta
import datetime
import urllib

from .models import *

def index(request, year, race_slug, distance_slug):
    namedevent = namedtuple('ne', ['event', 'individual_results', 'team_results'])
    namediresult = namedtuple('ni', ['place', 'female_athlete', 'female_time', 'male_athlete', 'male_time'])
    namedtresult = namedtuple('nt', ['team_category', 'top', 'winning_team', 'total_time', 'avg_time'])
    individual_results = []
    if distance_slug == 'combined':
        event = False
        results = Endurraceresult.objects.filter(year=year).order_by('guntime')
        hasmasters = Endurraceresult.objects.hasmasters(year)
        team_results = []
    else:
        event = Event.objects.get(race__slug=race_slug,
                                  distance__slug=distance_slug,
                                  date__icontains=year)
        results = Result.objects.filter(event_id=event.id)
        hasmasters = Result.objects.hasmasters(event)
        team_results = Teamresult.objects.of_event(event)
    female_results = list(results.filter(gender="F").values_list('athlete', 'guntime')[0:3])
    male_results = list(results.filter(gender="M").values_list('athlete', 'guntime')[0:3])
    for i in range(1,4):
        if i == 1:
            rank = '1st OA'
        elif i == 2:
            rank = '2nd OA'
        elif i == 3:
            rank = '3rd OA'
        female_guntime = female_results[i-1][1]
        female_time = female_guntime - timedelta(microseconds=female_guntime.microseconds)
        male_guntime = male_results[i-1][1]
        male_time = male_guntime - timedelta(microseconds=male_guntime.microseconds)
        individual_results.append(namediresult(rank, female_results[i-1][0], female_time, male_results[i-1][0], male_time))
    if hasmasters:
        if distance_slug == 'combined':
            individual_results.append(Endurraceresult.objects.topmasters(year))
        else:
            individual_results.append(Result.objects.topmasters(event))
    hill_results = False
    if race_slug == 'baden-road-races' and distance_slug == '7-mi':
        hill_results = []
        rank = '1st OA'
        try:
            male_prime = Prime.objects.filter(event=event, gender='M').order_by('time', 'place')[:1][0]
        except:
            hill_results = False
        else:
            male_result = results.get(place=male_prime.place)
            female_prime = Prime.objects.filter(event=event, gender='F').order_by('time', 'place')[:1][0]
            female_result = results.get(place=female_prime.place)
            hill_results.append(namediresult(rank, female_result.athlete, female_prime.time, male_result.athlete, male_prime.time))
    context = {'event': event,
               'distance_slug': distance_slug,
               'year': year,
               'individual_results': individual_results,
               'team_results': list(team_results),
               'hill_results': hill_results,
               'nomenu': True}
    return render(request, 'racedbapp/recap.html', context)
