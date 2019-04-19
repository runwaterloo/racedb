#!/usr/bin/env python
from django.core.management.base import BaseCommand
from collections import defaultdict
from racedbapp.models import Result


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = Result.objects.filter(event__date__gte="2013-01-01")
        people = defaultdict(int)
        for i in results:
            people[i.athlete] += 1
        freq = defaultdict(int)
        for i in range(1, 150):
            for _k, v in people.items():
                if v == i:
                    freq[i] += 1
        for k, v in freq.items():
            print("{}, {}".format(k, v))
        for k, v in people.items():
            if v >= 50:
                print(k, v)
