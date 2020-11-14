import datetime
import urllib
from collections import namedtuple
from datetime import timedelta

from django import db
from django.db.models import Count, Min
from django.http import HttpResponse
from django.shortcuts import render

from .models import *


def index(request):
    return render(request, "racedbapp/search.html")
