#!/usr/bin/env python
import operator
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = Result.objects.filter(
            rwmember__isnull=False,
        )
        member_races = defaultdict(list)
        for i in results:
            if not i.rwmember.active:
                continue
            if i.event.race.slug not in member_races[i.rwmember.name]:
                member_races[i.rwmember.name].append(i.event.race.slug)
        count = [(x, len(y)) for (x, y) in member_races.items()]
        sorted_count = sorted(count, key=operator.itemgetter(0))
        sorted_count = sorted(sorted_count, key=operator.itemgetter(1), reverse=True)
        for k, v in sorted_count:
            print("{},{}".format(k, v))
