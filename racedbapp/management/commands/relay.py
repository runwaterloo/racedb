#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from collections import defaultdict
import operator
from racedbapp.models import Relay
from datetime import datetime, timedelta

class Command(BaseCommand):

    def handle(self, *args, **options):
        with open("/run/secrets/1.csv") as f:
            lines = f.readlines()
        results = []
        print(Relay)
        for i in lines:
            line = i.strip()
            parts = line.split(",")
            t = datetime.strptime(parts[5],"%H:%M:%S")
            delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            thisresult = Relay(event_id=parts[0],
                               place=parts[1],
                               relay_team=parts[3],
                               relay_team_place=parts[4],
                               relay_team_time=delta,
                               relay_leg=parts[2])
            results.append(thisresult)
        for i in results:
            i.save()
