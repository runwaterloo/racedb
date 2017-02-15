from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Min, Count
from django import db
import simplejson
from collections import namedtuple
import urllib
from . import utils
from . import view_shared
from .models import *

def index(request, race_slug, distance_slug):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    namedresult = namedtuple('nr', ['place', 'guntime', 'athlete',
                                    'year', 'category',
                                    'city'])
    nameddistance = namedtuple('nd', ['id', 'name', 'slug', 'km'])
    namedrace = namedtuple('nr', ['id', 'name', 'shortname', 'slug'])
    rawrace = Race.objects.get(slug=race_slug)
    race = namedrace(rawrace.id, rawrace.name, rawrace.shortname, rawrace.slug)
    if distance_slug == 'combined':
        distance = nameddistance(0, 'Combined', distance_slug, 13)
    else:
        rawdistance = Distance.objects.get(slug=distance_slug)
        distance = nameddistance(rawdistance.id, rawdistance.name, rawdistance.slug, rawdistance.km)
    records, team_records, hill_records = view_shared.getracerecords(race, distance)
    context = {'race': race,
               'distance': distance,
               'records': records,
               'team_records': team_records,
               'hill_records': hill_records,
               'nomenu': True}

    # Determine the format to return based on what is seen in the URL
    if 'format' in qstring:
        if qstring['format'][0] == 'json':
            data = simplejson.dumps(context,
                                    default=str,
                                    indent=4,
                                    sort_keys=True)
            if 'callback' in qstring:
                callback = qstring['callback'][0]
                data = '{}({});'.format(callback, data)
                return HttpResponse(data, "text/javascript")
            else:
                return HttpResponse(data, "application/json")
        else:
            return HttpResponse('Unknown format in URL', "text/html")
    else:
        return render(request, 'racedbapp/records.html', context)
