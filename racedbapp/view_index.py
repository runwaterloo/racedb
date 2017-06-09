from django.shortcuts import render
#from django.db.models import Min, Q
#from django import db
from collections import namedtuple
#import urllib
#from . import utils
from datetime import datetime
from .models import *

def index(request):
    today = datetime.today()
    future_events = Event.objects.filter(date__gte=today).order_by('date', '-distance__km')
    context = {'future_events': future_events,
              }
    return render(request, 'racedbapp/index.html', context)
