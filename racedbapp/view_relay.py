from django.http import HttpResponse, Http404
from django.shortcuts import render
from urllib import parse
from . import view_shared
from .models import (
    Event
    )

#from collections import namedtuple
#from . import view_shared, utils
#from django.db.models import Count, Max, Q
#from datetime import timedelta
#from operator import attrgetter

def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    event = get_event(year, race_slug, distance_slug)
    team_categories = view_shared.get_team_categories(event)
    page = 'Relay'
    pages = view_shared.get_pages(event, 'Relay', team_categories, laurier_relay_dict=True)
    context = {
        'event': EventV(event),
        'pages': pages,
        }
    return render(request, 'racedbapp/relay.html', context)


def get_event(year, race_slug, distance_slug):
    """ Get the event based on query parameters or return 404 """
    try:
        event = Event.objects.select_related().get(
            race__slug=race_slug,
            distance__slug=distance_slug,
            date__icontains=year
            )
    except:
        raise Http404('Event not found')
    return event


class EventV:
    def __init__(self, event):
        self.city = event.city
        self.date = event.date
        self.flickrsetid = event.flickrsetid
        self.youtube_id = event.youtube_id
        self.distance_name = event.distance.name
        self.race_name = event.race.name
        self.race_shortname = event.race.shortname
        self.race_slug = event.race.slug
