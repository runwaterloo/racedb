from django.shortcuts import render
#from urllib import parse
#from collections import namedtuple
from .models import *
#from operator import attrgetter

def index(request):
    members = Rwmember.objects.filter(active=True)
    try:
        no_camera_tag = Rwmembertag.objects.get(name="no-profile-camera")
    except:
        no_camera_members = []
    else:
        no_camera_members = Rwmember.objects.filter(tags=no_camera_tag)
    context = {
               'members': members,
               'no_camera_members': no_camera_members,
              }
    return render(request, 'racedbapp/members.html', context)
