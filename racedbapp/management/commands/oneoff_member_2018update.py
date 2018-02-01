#!/usr/bin/env python
from django.core.management.base import BaseCommand, CommandError
from racedbapp.models import * 

class Command(BaseCommand):

    def handle(self, *args, **options):

        enabled = False

        if not enabled:
            print('Not enabled, exiting')
            exit()
        with open('/tmp/2018.txt', 'r') as f:
            renewals = f.readlines()
        renewals = [int(x) for x in renewals]
        tag = Rwmembertag.objects.get(name='member-2018')
        #newthing_tag = Rwmembertag.objects.get(name='newthing-2018')

        # Add tag for renewals
        for i in renewals:
            member = Rwmember.objects.get(id=i)
            print('Adding member-2018 tag to {}'.format(member))
            member.tags.add(tag)
            member.save()

        # Deactivate lapsed
        for member in Rwmember.objects.exclude(tags=tag):
            print(member.id, member.name)
            #print('Deactivating {}'.format(member.name))
            #member.active = False
            #member.save()

        # Apply new thing tag to active tags
        #for member in Rwmember.objects.filter(active=True, tags=tag):
        #    print('Adding newthing to {}'.format(member))
        #    member.tags.add(newthing_tag)
        #    member.save()


