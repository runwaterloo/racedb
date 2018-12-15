#!/usr/bin/env python
from django.core.management.base import BaseCommand
from racedbapp.models import Rwmember, Rwmembertag


class Command(BaseCommand):
    def handle(self, *args, **options):

        enabled = False
        if not enabled:
            print("Not enabled, exiting")
            exit()

        db_members = Rwmember.objects.values_list("slug", flat=True)
        new_members = []
        existing_members = []
        with open("/tmp/m.txt", "r") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            parts = line.split(",")
            name = parts[0]
            slug = parts[1]
            gender = parts[2]
            yob = parts[3]
            city = parts[4]
            joindate = parts[5]
            photourl = parts[6]
            altname = parts[7]
            active = parts[8]
            if active == "Yes":
                active = True
            else:
                active = False
            thismember = Rwmember(
                name=name,
                slug=slug,
                gender=gender,
                year_of_birth=yob,
                city=city,
                joindate=joindate,
                photourl=photourl,
                altname=altname,
                active=active,
            )
            if slug in db_members:
                existing_members.append(thismember)
            else:
                new_members.append(thismember)
        tag1 = Rwmembertag.objects.get(name="member-2019")
        tag2 = Rwmembertag.objects.get(name="boost-2019")

        # Renew existing
        for i in existing_members:
            member = Rwmember.objects.get(slug=i.slug)
            print("Adding member-2019 tag to {}".format(member))
            member.tags.add(tag1)
            member.active = i.active
            if i.active:
                print("Adding boost-2019 tag to {}".format(member))
                member.tags.add(tag2)
            member.city = i.city
            member.save()

        # Add new
        for i in new_members:
            print("Adding {}".format(i))
            i.save()
            member = Rwmember.objects.get(slug=i.slug)
            member.tags.add(tag1)
            if member.active:
                member.tags.add(tag2)
            member.save()

        # Deactivate lapsed
        # for member in Rwmember.objects.exclude(tags=tag):
        #    print(member.id, member.name)
        #    #print('Deactivating {}'.format(member.name))
        #    #member.active = False
        #    #member.save()
