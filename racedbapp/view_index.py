from django.shortcuts import render
#from django.http import HttpResponse
#from django.db.models import Min, Q
#from django import db
#from collections import namedtuple
#import urllib
#from . import utils
from .models import *

def index(request):
    context = {}
    return render(request, 'racedbapp/index.html', context)
