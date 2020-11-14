#!/usr/bin/env python
""" parseresults.py - Race result parsing utility. """
import datetime
import json
import os

import requests
from django.core.management.base import BaseCommand, CommandError
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from racedbapp.models import *

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import logging
import sys

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
    "4049",
    "5059",
    "6069",
]


class Command(BaseCommand):
    help = "Updates wheelchair results from pre"

    def handle(self, *args, **options):
        results = []
        resultsurl = "http://pre.scrw.ca/api/wheelchairresults/"
        while True:
            r = requests.get(resultsurl)
            pageresults = r.json()["results"]
            for result in pageresults:
                resultcategory = result["category"]
                try:
                    category = Category.objects.get(name=resultcategory)
                except:
                    ismasters = False
                    for i in MASTERS_SUBSTRINGS:
                        if i in resultcategory:
                            ismasters = True
                        category = Category(name=resultcategory, ismasters=ismasters)
                        category.save()
                guntime = maketimedelta(result["guntime"])
                chiptime = maketimedelta(result["chiptime"])
                if guntime != chiptime:
                    gun_equal_chip = False
                newresult = Wheelchairresult(
                    event_id=result["event"],
                    place=result["place"],
                    bib=result["bib"],
                    athlete=result["athlete"],
                    gender=result["gender"],
                    category=category,
                    city=result["city"],
                    chiptime=chiptime,
                    guntime=guntime,
                )
                results.append(newresult)
            if r.json()["next"]:
                resultsurl = r.json()["next"]
            else:
                break
        # Delete any existing results
        Wheelchairresult.objects.all().delete()
        for result in results:
            result.save()
        info = "{} wheelchair results processed".format(len(results))
        logger.info(info)
        self.stdout.write(info)


def maketimedelta(strtime):
    if "." in strtime:
        microsec = strtime.split(".")[1]
        if int(microsec) == 0:
            milliseconds = 0
        else:
            if microsec[0] == 0:
                milliseconds = int(microsec) / 10000
            else:
                milliseconds = int(microsec) / 1000
        hours, minutes, seconds = strtime.split(".")[0].split(":")
    else:
        milliseconds = 0
        hours, minutes, seconds = strtime.split(":")
    timedelta = datetime.timedelta(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        milliseconds=milliseconds,
    )
    return timedelta
