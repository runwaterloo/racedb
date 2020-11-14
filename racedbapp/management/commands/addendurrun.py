#!/usr/bin/env python
""" Add endurrun athletes

Needs a csv file with the following fields:
 - year
 - division
 - athlete name
 - gender
 - age
 - city
 - province
 - country

"""
import csv
import logging
import os
import sys

from django.core.management.base import BaseCommand, CommandError

from racedbapp.models import *

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Adds bow athletes from csv file"

    def handle(self, *args, **options):
        with open("/tmp/endur_athletes.csv") as csvfile:
            endurathletes = csv.reader(csvfile, delimiter=",")
            for a in endurathletes:
                year = a[0]
                division = a[1]
                name = a[2]
                gender = a[3]
                age = a[4]
                city = a[5]
                province = a[6]
                country = a[7]
                newathlete = Endurathlete(
                    year=year,
                    division=division,
                    name=name,
                    gender=gender,
                    age=age,
                    city=city,
                    province=province,
                    country=country,
                )
                newathlete.save()
