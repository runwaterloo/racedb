from django import db
from django.http import HttpResponse
from django.shortcuts import render

from .models import *


def index(request):
    return render(request, "racedbapp/endurrunhome.html")
