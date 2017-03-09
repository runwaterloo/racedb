from django.shortcuts import render
#from urllib import parse
#from collections import namedtuple
from .models import *
#from operator import attrgetter

def index(request):
    members = Rwmember.objects.filter(active=True)
    member_tags = list(Phototag.objects.values_list('tag', flat=True).distinct().filter(tag__startswith='m'))
    member_tags = [x.lstrip('m') for x in member_tags]
    member_tags = [int(x) for x in member_tags if x.isdigit()]
    context = {
               'members': members,
               'member_tags': member_tags,
              }
    return render(request, 'racedbapp/members.html', context)
