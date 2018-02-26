from django.http import HttpResponse, Http404
from django.shortcuts import render
from collections import namedtuple
from urllib import parse
from . import view_shared
from .models import (
    Event,
    Relay,
    )

named_filter = namedtuple('nf', ['current', 'choices'])
named_choice = namedtuple('nc', ['name', 'url'])

#from . import view_shared, utils
#from django.db.models import Count, Max, Q
#from datetime import timedelta
#from operator import attrgetter

def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    event = get_event(year, race_slug, distance_slug)
    relay_results = get_relay_results(event)
    team_categories = view_shared.get_team_categories(event)
    page = 'Relay'
    pages = view_shared.get_pages(
        event,
        'Relay',
        team_categories,
        laurier_relay_dict=True,
        )
    filters = {
        'year_filter': get_year_filter(event),
    }
    context = {
        'event': EventV(event),
        'pages': pages,
        'filters': filters,
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


def get_relay_results(event):
    relay_results = Relay.objects.filter(event=event)
    if len(relay_results) == 0:
        raise Http404('No results found')
    return relay_results


def get_year_filter(event):
    rawresults = Relay.objects.select_related().filter(event__race=event.race)
    dates = rawresults.order_by('-event__date').values_list('event__date', 'event__race__slug').distinct()
    choices = []
    for d in dates:
        year = d[0].year
        if year == event.date.year:
            continue
        choices.append(named_choice(year, '/relay/{}/{}/{}/'.format(year, d[1], event.distance.slug)))
    year_filter = named_filter(event.date.year, choices)
    return year_filter


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
