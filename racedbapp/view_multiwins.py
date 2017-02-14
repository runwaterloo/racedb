from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Min, Count
from django import db
from collections import namedtuple
from operator import itemgetter, attrgetter
import urllib

from .models import *
from . import view_shared

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    gender = False
    if 'gender' in qstring:
        gender = qstring['gender'][0]
    #races = qstring['race']
    namedwinner = namedtuple('nw', ['rank', 'wins', 'gender', 'athlete', 'member'])
    malewinnersdict, femalewinnersdict = view_shared.getwinnersdict()
    femalewinnerscount = {}
    femalewinners = []
    for k, v in femalewinnersdict.items():
        if v.athlete.lower() in femalewinnerscount:
            femalewinnerscount[v.athlete.lower()] += 1
        else:
            femalewinnerscount[v.athlete.lower()] = 1
    for k, v in femalewinnerscount.items():
        if v > 1:
            femalewinners.append(namedwinner(0, v, 'F', k.title(), False))
    femalewinners = sorted(femalewinners, reverse=True)
    malewinnerscount = {}
    for k, v in malewinnersdict.items():
        if v.athlete.lower() in malewinnerscount:
            malewinnerscount[v.athlete.lower()] += 1
        else:
            malewinnerscount[v.athlete.lower()] = 1
    malewinners = []
    for k, v in malewinnerscount.items():
        if v > 1:
            malewinners.append(namedwinner(0, v, 'M', k.title(), False))
    combinedwinners = malewinners + femalewinners
    rawwinners = sorted(combinedwinners, key=attrgetter('athlete'))
    finalwinners = sorted(rawwinners, key=attrgetter('wins'), reverse=True)
    winners = []
    lastwins = 0
    count = 1
    member_dict = view_shared.get_member_dict()
    for i in finalwinners:
       if gender:
           if i.gender.lower() != gender:
               continue
       if i.wins != lastwins:
          rank = count
       member = False
       if i.athlete.lower() in member_dict:
           member = member_dict[i.athlete.lower()]
       winners.append(namedwinner(rank, i.wins, i.gender, i.athlete, member))
       lastwins = i.wins
       count += 1
    namedfilter = namedtuple('nf', ['current', 'choices'])                       
    namedchoice = namedtuple('nc', ['name', 'url'])            
    choices = []
    if gender:
        choices.append(namedchoice('', '/multiwins'))
        if gender == 'm':
            current = 'Male'
        else:
            current = 'Female'
    else:
        current = ''
    if gender != 'f':
        choices.append(namedchoice('Female', '/multiwins?gender=f'))
    if gender != 'm':
        choices.append(namedchoice('Male', '/multiwins?gender=m'))
    genderfilter = namedfilter(current, choices)
    context = {'winners': winners, 'genderfilter': genderfilter}
    return render(request, 'racedbapp/multiwins.html', context)
