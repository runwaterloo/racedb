from django.shortcuts import render
from django.http import HttpResponse
from django import db

from .models import *

def index(request):
    return render(request, 'racedbapp/endurrunhome.html')
