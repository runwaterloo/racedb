#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        tag = Rwmembertag.objects.get(name="member-2017")
        # for i in Rwmember.objects.filter(tags=tag):
        #    event_count = Result.objects.filter(event__date__contains='2017', rwmember=i).count()
        #    print('{},{}'.format(i, event_count))
        for i in Event.objects.filter(date__contains="2017").order_by("date"):
            member_results = Result.objects.filter(event=i, rwmember__tags=tag).count()
            print("{},{}".format(i, member_results))
