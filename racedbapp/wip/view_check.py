from django.shortcuts import render
from django.http import JsonResponse
from django import db
from .models import *

def index(request, year, race_slug, distance_slug):
    try:
        event = Event.objects.get(race__slug=race_slug,
                                  distance__slug=distance_slug,
                                  date__icontains=year)
    except:
        event_exists = False
    else:
        event_exists = True
    if event_exists:
        results = Result.objects.filter(event=event).first()
        if results:
            has_results = True
        else:
            has_results = False
    else:
        has_results = False
    response = {'event_exists': event_exists,
               'has_results': has_results}
    return JsonResponse(response)
