from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import render
from collections import namedtuple
from operator import attrgetter
from urllib import parse
from . import view_shared
from .models import (
    Event,
    Durelay,
    )

def index(request, year):
    duresults = Durelay.objects.filter(year=year)
    if len(duresults) == 0:
        raise Http404('No results found')
    context = {
        'year': year,
        'duresults': duresults,
        }
    return render(request, 'racedbapp/durelay.html', context)
