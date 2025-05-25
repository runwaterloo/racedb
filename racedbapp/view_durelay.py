from django.http import Http404
from django.shortcuts import render

from .models import Durelay


def index(request, year):
    duresults = Durelay.objects.filter(year=year)
    if len(duresults) == 0:
        raise Http404("No results found")
    context = {
        "year": year,
        "duresults": duresults,
    }
    return render(request, "racedbapp/durelay.html", context)
