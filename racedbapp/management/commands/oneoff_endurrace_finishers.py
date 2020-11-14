#!/usr/bin/env python
import operator
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        endurrace_results = Result.objects.filter(
            event__race__slug="endurrace",
            rwmember__isnull=False,
        ).order_by("event__date")
        member_years = defaultdict(list)
        member_count = defaultdict(int)
        for i in endurrace_results:
            if not i.rwmember.active:
                continue
            if i.event.date.year in member_years[i.rwmember.name]:
                member_count[i.rwmember.name] += 1
            else:
                member_years[i.rwmember.name].append(i.event.date.year)
        sorted_member_count = sorted(member_count.items(), key=operator.itemgetter(0))
        sorted_member_count = sorted(
            sorted_member_count, key=operator.itemgetter(1), reverse=True
        )
        for k, v in sorted_member_count:
            print("{},{}".format(k, v))
