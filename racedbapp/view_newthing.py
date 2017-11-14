from django.shortcuts import render
from .models import *

def index(request):
    stuff = None
    context = {
               'stuff': stuff,
              }
    return render(request, 'racedbapp/newthing.html', context)
