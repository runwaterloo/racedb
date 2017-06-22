from django.shortcuts import render
from django.http import HttpResponse
#from django.db.models import Min, Q
#from django import db
from collections import namedtuple
import urllib
import simplejson
from . import view_recap, view_member
from datetime import datetime
from .models import *

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    today = datetime.today()
    lastraceday = get_lastraceday()
    memberinfo = get_memberinfo()
    future_events = Event.objects.filter(date__gte=today).order_by('date', '-distance__km')
    context = {'lastraceday': lastraceday,
               'memberinfo': memberinfo,
               'future_events': future_events,
              }
    # Determine the format to return based on what is seen in the URL            
    if 'format' in qstring:                                                      
        if qstring['format'][0] == 'json':                                       
            data = simplejson.dumps(context,                                     
                                    default=str,                                 
                                    indent=4,                                    
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
        return render(request, 'racedbapp/index.html', context)

def get_lastraceday():
    lastraceday = []
    named_lastraceday = namedtuple('nl', ['event', 'recap', 'finishers'])
    date_of_last_event = (Result.objects.all()
                          .order_by('-event__date')[:1][0]
                          .event.date)
    last_day_events = Event.objects.filter(date=date_of_last_event)
    for lde in last_day_events:
        event_results = Result.objects.filter(event=lde)
        finishers = event_results.filter(place__lte=990000).count()
        hasmasters = Result.objects.hasmasters(lde)
        distance_slug = lde.distance.slug
        individual_recap = view_recap.get_individual_results(lde, event_results, hasmasters, distance_slug)
        lastraceday.append(named_lastraceday(lde, individual_recap, finishers))
    return lastraceday

def get_memberinfo():
    num_recent_badges = 4
    named_memberinfo = namedtuple('nm', ['member', 'racing_since', 'km', 'badges'])
    member = Rwmember.objects.filter(active=True).exclude(photourl=None).exclude(photourl='').order_by('?')[:1][0]
    member_results, km = view_member.get_memberresults(member)
    km = round(km, 1)
    racing_since = ''
    if len(member_results) > 0:
        racing_since = member_results[-1].result.event.date.year
    recent_badges = view_member.get_badges(member, member_results)[0:num_recent_badges]
    memberinfo = named_memberinfo(member, racing_since, km, recent_badges)
    return memberinfo
