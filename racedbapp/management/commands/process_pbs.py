#!/usr/bin/env python
""" Process PBs """
from django.core.management.base import BaseCommand, CommandError
from racedbapp.models import * 
#import os
#import datetime
#import json
#import requests
#from requests.packages.urllib3.exceptions import InsecureRequestWarning
#requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
#import sys
import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process PBs for an event (and all subsequent events)'

    def add_arguments(self, parser):
        parser.add_argument('-e',
        action='store',
        dest='event',
        default=False,
        required=True)

    def handle(self, *args, **options):
        event = Event.objects.get(id=options['event'])
        members = Result.objects.values('rwmember_id').filter(event=event, rwmember__isnull=False).values_list('rwmember_id', flat=True)
        rwpbs = dict(Rwmember.objects.filter(result__event__distance=event.distance,
                                             result__event__date__lt=event.date,
                                             result__rwmember_id__in=members).annotate(rwpb=Min('result__guntime')).values_list('id', 'result__guntime'))
        future_results = Result.objects.filter(event__date__gte=event.date, event__distance=event.distance, rwmember_id__in=members).order_by('event__date')
        for i in future_results:
            i.isrwpb = False
            if i.rwmember_id in rwpbs:
                if i.guntime < rwpbs[i.rwmember_id]:
                    rwpbs[i.rwmember_id] = i.guntime
                    i.isrwpb = True
            else:
                rwpbs[i.rwmember_id] = i.guntime
                i.isrwpb = True
            i.save()
