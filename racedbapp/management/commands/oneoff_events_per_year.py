#!/usr/bin/env python
from django.core.management.base import BaseCommand
from collections import defaultdict
from racedbapp.models import Event, Result, Rwmember, Rwmembertag
import operator


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "-y",
            action="store",
            dest="year",
        )
    def handle(self, *args, **options):
        year = options["year"]
        tag = Rwmembertag.objects.get(name='member-{}'.format(year))
        members = Rwmember.objects.filter(tags=tag)
        results = Result.objects.filter(event__date__contains=year)
        members_count = defaultdict(int)
        nonmembers_count = defaultdict(int)
        for i in results:
            if i.rwmember in members:
                members_count[i.rwmember] += 1
            else:
                nonmembers_count[i.athlete] += 1
        print("MEMBERS")
        sorted_members_count = sorted(members_count.items(), key=operator.itemgetter(1), reverse=True)
        for k, v in sorted_members_count:
            print("{},{}".format(k, v))
        print("NON-MEMBERS")
        sorted_nonmembers_count = sorted(nonmembers_count.items(), key=operator.itemgetter(1), reverse=True)
        for k, v in sorted_nonmembers_count:
            print("{},{}".format(k, v))
