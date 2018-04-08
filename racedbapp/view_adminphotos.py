from django.shortcuts import render, redirect
from django.http import HttpResponse
from collections import namedtuple
from .models import *

def index(request):
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/adminphotos/')            
    notifykey = Config.objects.get(name='notifykey').value
    dbevents = Event.objects.select_related().order_by('-date', '-distance__km').exclude(flickrsetid=None)
    event_results_dict = dict(Event.objects.annotate(num_results=Count('result')).values_list('id', 'num_results'))
    event_tags_dict = dict(Phototag.objects.values('event_id').annotate(Count('tag')).values_list('event_id', 'tag__count'))
    named_event = namedtuple('ne', ['event',
                                    'num_results',
                                    'unique_tags',
                                    'pct'])
    events = []
    for e in dbevents:
        num_results = event_results_dict[e.id]
        if num_results == 0:
            continue
        try:
            num_tags = event_tags_dict[e.id]
        except:
            num_tags = 0
        pct = '{:.1%}'.format(num_tags / num_results)
        events.append(named_event(e,
                                  num_results,
                                  num_tags,
                                  pct))
    context = {'events': events,
               'notifykey': notifykey}
    return render(request, 'racedbapp/adminphotos.html', context)
