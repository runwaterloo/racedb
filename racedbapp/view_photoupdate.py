from django.http import JsonResponse
import urllib
import json
import flickrapi    # https://stuvel.eu/flickrapi
from .models import *
from . import secrets
import logging                                                                   
logger = logging.getLogger(__name__)   

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    notifykey = Config.objects.filter(name='notifykey')[0].value
    if 'notifykey' not in qstring:
        logger.error('missing key')
        response = {'result': 'fail',
                    'message': 'missing key'}
    elif qstring['notifykey'][0] != notifykey:
        logger.error('invalid key')
        response = {'result': 'fail',
                    'message': 'invalid key'}
    elif 'date' not in qstring:
        logger.error('missing date')
        response = {'result': 'fail',
                    'message': 'missing date'}
    else:
        date = qstring['date'][0]
        events = Event.objects.filter(date=date)
        if len(events) == 0:
            logger.warning('no events found for {}'.format(date))
            response = {'result': 'fail',
                        'message': 'no events found for {}'.format(date)}
        else:
            update_event_tags(events)
            response = {'result': 'success',
                        'message': 'thank you, come again!'}
    return JsonResponse(response)

def update_event_tags(events):
    logger.info('Starting photo tag update for {} events'.format(len(events)))
    for event in events:
        runwaterloo_flickr_id = '136573113@N04'
        photos_per_page = 500
        flickr = flickrapi.FlickrAPI(secrets.flickr_api_key, secrets.flickr_secret_key, format='parsed-json')
        photos_page1 = flickr.photos.search(user_id=runwaterloo_flickr_id,
                                        tag_mode='all',
                                        tags='{},{}'.format(event.date.year,
                                                            event.race.slug),
                                        per_page=photos_per_page,
                                        extras='tags')
        numpages = int(photos_page1['photos']['pages'])
        photos_all = photos_page1['photos']['photo']
        page = 1
        while page < numpages:
            page += 1
            photos_pageX = flickr.photos.search(user_id=runwaterloo_flickr_id,
                                                tag_mode='all',
                                                tags='{},{}'.format(event.date.year,
                                                                    event.race.slug),
                                                per_page=photos_per_page,
                                                page=page,              
                                                extras='tags')
            photos_all += photos_pageX['photos']['photo']
        tags = []
        for p in photos_all:
            tags += p['tags'].split()
        tags = sorted(set(tags))
        Phototag.objects.filter(event=event).delete()
        dbtags = []
        for t in tags:
            dbtags.append(Phototag(event=event, tag=t))
        Phototag.objects.bulk_create(dbtags)
        logger.info('Found {} tags for {}'.format(len(tags), event))
