from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Min, Count
from django import db
from collections import namedtuple
from datetime import timedelta
import datetime
import urllib

from .models import *

def index(request):
    return render(request, 'racedbapp/search.html')
