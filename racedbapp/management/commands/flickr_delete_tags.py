#!/usr/bin/env python
""" flickr_delete_tags.py - delete tags from Flickr """
from django.core.management.base import BaseCommand, CommandError
#import os
#import sys
import logging
import flickrapi
from racedb import secrets
from racedbapp.models import *
from racedbapp.view_photoupdate import get_event_photos

logger = logging.getLogger(__name__)
runwaterloo_flickr_id = '136573113@N04'                                          
photos_per_page = 500                                                            
flickr = flickrapi.FlickrAPI(secrets.FLICKR_API_KEY,                             
                             secrets.FLICKR_SECRET_KEY,                          
                             format='parsed-json')      

class Command(BaseCommand):
    help = 'Delete tags from Flickr'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e', '--event',
            action='store',
            required=True,
            help='Event id')

    def handle(self, *args, **options):
        author_to_delete = 'Sam17378'
        event = Event.objects.get(id=options['event'])
        go = input('Remove {} tags from {} {} {}? (y/n): '.format(author_to_delete, event.date.year, event.race.shortname, event.distance.name))
        if go != 'y':
            exit(0)
        photos = get_event_photos(event)
        tags_deleted = 0
        tags_untouched = 0
        for p in photos:
            details = flickr.photos.getinfo(photo_id=p['id'])
            tags = details['photo']['tags']['tag']
            for t in tags:
                if t['authorname'] == author_to_delete:
                    flickr.photos.removetag(tag_id=t['id'])
                    logger.info('Delete tag: event={} photo_id={} tag_content={} tag_id={}'.format(event.id, p['id'], t['_content'], t['id']))
                    tags_deleted += 1
                else:
                    tags_untouched += 1
        print('{} photos processed'.format(len(photos)))
        print('{} tags deleted'.format(tags_deleted))
        print('{} tags untouched'.format(tags_untouched))
