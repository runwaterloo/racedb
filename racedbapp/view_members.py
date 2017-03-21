from django.shortcuts import render
#from urllib import parse
#from collections import namedtuple
from .models import *
#from operator import attrgetter

def index(request):
    members = Rwmember.objects.filter(active=True)
    context = {
               'members': members,
              }
    return render(request, 'racedbapp/members.html', context)
