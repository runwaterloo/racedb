from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.db.models import Min, Count, Q
from django import db
from collections import namedtuple
from datetime import timedelta
import datetime
import urllib
import re

from .models import *
from . import utils, view_shared

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    message = ''
    if 'q' not in qstring:
        raise Http404('No search string provided')
    q = qstring['q'][0]
    name_query = get_query(q, ['athlete',])
    dbresults = Result.objects.filter(name_query)
    if len(dbresults) > 200:
        results = False
        message = 'Too many results. Please search for something more specific.'
    elif len(dbresults) == 0:
        results = False
        message = 'No results found.'
    else:
        results = []
        namedresult = namedtuple('nr', ['event', 'athlete', 'place',
                                        'bib', 'guntime',
                                        'category', 'catplace',
                                        'catcount', 'genderplace',
                                        'chiptime', 'city', 'member'])
        for result in dbresults.order_by('-event__date'):
            guntime = result.guntime - timedelta(microseconds=result.guntime.microseconds)
            catplace = Result.objects.filter(event=result.event, category=result.category, place__lte=result.place).count()
            catcount = Result.objects.filter(event=result.event, category=result.category).count()
            genderplace = Result.objects.filter(event=result.event, gender=result.gender, place__lte=result.place).count()
            if result.chiptime:
                chiptime = result.chiptime - timedelta(microseconds=result.chiptime.microseconds)
            else:
                chiptime = ''
            member = None
            if result.rwmember:
                if result.rwmember.active:
                    member = result.rwmember
            results.append(namedresult(result.event,
                                       result.athlete,
                                       result.place,
                                       result.bib,
                                       guntime,
                                       result.category,
                                       catplace,
                                       catcount,
                                       genderplace,
                                       chiptime,
                                       result.city,
                                       member))

    context = {'q': q,
               'message': message,
               'results': results}
    #print(len(db.connection.queries))   # number of sql queries that happened
    return render(request, 'racedbapp/name.html', context)

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:

        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    '''
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.

    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query
