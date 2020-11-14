#!/usr/bin/env python
""" Add bow athletes

Needs a csv file with the following fields:
 - bow name
 - athlete name
 - gender
 - category

"""
import csv
import logging
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *

logger = logging.getLogger(__name__)

MASTERS_SUBSTRINGS = [
    "40-",
    "45-",
    "50-",
    "55-",
    "60-",
    "65-",
    "70-",
    "75-",
    "40+",
    "50+",
    "60+",
    "70+",
    "MST",
]


class Command(BaseCommand):
    help = "Adds bow athletes from csv file"

    def handle(self, *args, **options):
        with open("/tmp/bow_athletes.csv") as csvfile:
            bowathletes = csv.reader(csvfile, delimiter=",")
            for a in bowathletes:
                bow = Bow.objects.get(name=a[0])
                athlete = a[1]
                gender = a[2]
                category = Category.objects.get(name=a[3])
                newathlete = Bowathlete(
                    bow=bow, name=athlete, gender=gender, category=category
                )
                newathlete.save()
