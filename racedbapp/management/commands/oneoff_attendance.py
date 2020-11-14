#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = []
        races = Race.objects.all()
        events = Event.objects.all()
        years = sorted(set([x.date.year for x in events]))
        for r in races:
            thisr = [
                r.name,
            ]
            for y in years:
                thisr.append(
                    Result.objects.filter(
                        event__date__contains=y, event__race=r
                    ).count()
                )
            results.append(thisr)
        for r in results:
            print(r)

        # for i in Rwmember.objects.filter(tags=tag):
        #    event_count = Result.objects.filter(event__date__contains='2017', rwmember=i).count()
        #    print('{},{}'.format(i, event_count))
        # for i in Event.objects.filter(date__contains='2017').order_by('date'):
        #    member_results = Result.objects.filter(event=i, rwmember__tags=tag).count()
        #    print('{},{}'.format(i, member_results))
