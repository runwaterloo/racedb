from django.shortcuts import render
from django.http import Http404
from urllib import parse
from collections import namedtuple
from .models import *
from . import view_shared, utils
from django.http import HttpResponse
from django.db.models import Count, Max, Q
from datetime import timedelta
from operator import attrgetter
import simplejson

def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    context = {}
    # Determine the format to return based on the query string
    if 'format' in qstring:
        if qstring['format'][0] == 'json':
            data = simplejson.dumps(context,
                                    default=str,
                                    indent=2,
                                    sort_keys=True)
            if 'callback' in qstring:
                callback = qstring['callback'][0]
                data = '{}({});'.format(callback, data)
                return HttpResponse(data, "text/javascript")
            else:
                return HttpResponse(data, "application/json")
        else:
            return HttpResponse('Unknown format in URL', "text/html")
    else:
        return render(request, 'racedbapp/relay.html', context)
