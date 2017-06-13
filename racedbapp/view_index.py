from django.shortcuts import render
#from django.db.models import Min, Q
#from django import db
from collections import namedtuple
#import urllib
from . import view_recap
from datetime import datetime
from .models import *

def index(request):
    today = datetime.today()
    lastraceday = get_lastraceday()
    future_events = Event.objects.filter(date__gte=today).order_by('date', '-distance__km')
    context = {'lastraceday': lastraceday,
               'future_events': future_events,
              }
    return render(request, 'racedbapp/index.html', context)

def get_lastraceday():
    lastraceday = []
    named_lastraceday = namedtuple('nl', ['event', 'recap', 'finishers'])
    date_of_last_event = (Result.objects.all()
                          .order_by('-event__date')[:1][0]
                          .event.date)
    last_day_events = Event.objects.filter(date=date_of_last_event)
    for lde in last_day_events:
        event_results = Result.objects.filter(event=lde)
        finishers = event_results.filter(place__lte=990000).count()
        hasmasters = Result.objects.hasmasters(lde)
        distance_slug = lde.distance.slug
        individual_recap = view_recap.get_individual_results(lde, event_results, hasmasters, distance_slug)
        lastraceday.append(named_lastraceday(lde, individual_recap, finishers))
    return lastraceday
