from django.http import JsonResponse
import urllib
from datetime import date, datetime, timedelta
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
        qsdate = qstring['date'][0]
        events = get_events(qsdate)
        if len(events) == 0:
            logger.warning('no events found for {}'.format(qsdate))
            response = {'result': 'fail',
                        'message': 'no events found for {}'.format(qsdate)}
        else:
            response = update_event_tags(events)
    json_dumps_params = {'indent': 4,}
    return JsonResponse(response, json_dumps_params=json_dumps_params)

def get_events(qsdate):
    today = date.today()
    hour = datetime.now().hour
    if qsdate == 'all':
        events = Event.objects.all().exclude(flickrsetid=None)
    elif qsdate == 'auto':
        if hour == 3:
            logger.info('Performing monthly auto (all events month anniversaries)')
            day = datetime.now().day
            events = Event.objects.filter(date__day=day).exclude(flickrsetid=None)
        elif hour == 6:
            logger.info('Performing daily auto (all events past year)')
            year_ago = today - timedelta(days=365)
            events = Event.objects.filter(date__gte=year_ago).exclude(flickrsetid=None)
        else:
            logger.info('Performing hourly auto (all events past month)')
            month_ago = today - timedelta(days=31)
            events = Event.objects.filter(date__gte=month_ago).exclude(flickrsetid=None)
    else:
        events = Event.objects.filter(date=qsdate).exclude(flickrsetid=None)
    return events

def update_event_tags(events):
    response = {}
    response['numevents'] = len(events)
    response['events'] = []
    logger.info('Starting photo tag update for {} events'.format(len(events)))
    for event in events:
        runwaterloo_flickr_id = '136573113@N04'
        photos_per_page = 500
        flickr = flickrapi.FlickrAPI(secrets.flickr_api_key,
                                     secrets.flickr_secret_key,
                                     format='parsed-json')
        photos_page1 = flickr.photos.search(user_id=runwaterloo_flickr_id,
                                        tag_mode='all',
                                        tags='{}{}{}'.format(event.date.year,
                                                             event.race.slug,
                                                             event.distance.slug),
                                        per_page=photos_per_page,
                                        extras='tags')
        numpages = int(photos_page1['photos']['pages'])
        photos_all = photos_page1['photos']['photo']
        page = 1
        while page < numpages:
            page += 1
            photos_pageX = flickr.photos.search(user_id=runwaterloo_flickr_id,
                                                tag_mode='all',
                                                tags='{}{}{}'.format(event.date.year,
                                                                     event.race.slug,
                                                                     event.distance.slug),
                                                per_page=photos_per_page,
                                                page=page,              
                                                extras='tags')
            photos_all += photos_pageX['photos']['photo']
        tags = []
        for p in photos_all:
            tags += p['tags'].split()
        tags = sorted(set(tags))
        if len(tags) > 0:
            tags = [ x for x in tags if x.lstrip('m').isdigit() ]
            dbtags = []
            for t in tags:
                dbtags.append(Phototag(event=event, tag=t))
            Phototag.objects.filter(event=event).delete()
            Phototag.objects.bulk_create(dbtags)
        logger.info('Processed {} tags for {}'.format(len(tags), event))
        thisresponse = {'event': str(event),
                        'numtags': len(tags),
                        'photos_scanned': len(photos_all),
                        'tags': str(tags),
                       }
        response['events'].append(thisresponse)
    response['result'] = 'success'
    response['message'] = 'thank you, come again!'
    return response
