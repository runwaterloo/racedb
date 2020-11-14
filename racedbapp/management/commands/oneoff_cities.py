#!/usr/bin/env python
import operator
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        results = Result.objects.filter(
            event__date__gte="2013-01-01",
            event__date__lte="2018-12-31",
        ).order_by("event__date")
        city_count = {}
        city_count["All"] = defaultdict(int)
        for i in results:
            # if i.event.race.name not in races:
            #    races.append(i.event.race.name)
            clean_city = get_clean_city(i.city)
            city_count["All"][clean_city] += 1
            year_race = "{} {}".format(i.event.date.year, i.event.race.name)
            if year_race not in city_count:
                city_count[year_race] = defaultdict(int)
            city_count[year_race][clean_city] += 1
        for i in city_count.keys():
            sorted_city_count = sorted(
                city_count[i].items(), key=operator.itemgetter(0)
            )
            sorted_city_count = sorted(
                sorted_city_count, key=operator.itemgetter(1), reverse=True
            )
            print()
            print(i.upper())
            for k, v in sorted_city_count:
                print("{},{}".format(k, v))


def get_clean_city(city):
    clean_city = city.title()
    if clean_city == "":
        clean_city = "Unknown City"
    return clean_city
