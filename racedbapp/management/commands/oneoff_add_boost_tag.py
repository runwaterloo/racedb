#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from racedbapp.models import * 

class Command(BaseCommand):

    def handle(self, *args, **options):

        enabled = False

        if not enabled:
            print('Not enabled, exiting')
            exit()
        member_tag = Rwmembertag.objects.get(name='member-2018')
        boost_tag = Rwmembertag.objects.get(name='boost-2017')
        boost_tag2 = Rwmembertag.objects.get(name='boost-2018')

        # Apply new thing tag to active tags
        for member in Rwmember.objects.filter(active=True, year_of_birth__isnull=False, tags=member_tag):
            print('Adding boost to {}'.format(member))
            member.tags.add(boost_tag)
            member.tags.add(boost_tag2)
            member.save()


