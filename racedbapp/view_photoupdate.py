from django.http import JsonResponse, StreamingHttpResponse
import urllib
from datetime import date, datetime, timedelta
import flickrapi    # https://github.com/sybrenstuvel/flickrapi
from .models import *
from . import secrets
from . import view_shared
import logging                                                                   
import json
logger = logging.getLogger(__name__)   
runwaterloo_flickr_id = '136573113@N04'
photos_per_page = 500
flickr = flickrapi.FlickrAPI(secrets.flickr_api_key,
                             secrets.flickr_secret_key,
                             format='parsed-json')


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
        logger.info('Starting photo tag update for {} ({})'.format(event, event.id))
        photos = get_event_photos(event)
        tags = get_tags(photos, event)
        oldtags = Phototag.objects.filter(event=event).values_list('tag', flat=True)
        if list(tags) == list(oldtags):
            logger.info('{} tags unchanged for {} ({})'.format(len(tags), event, event.id))
        else:
            dbtags = []
            for t in tags:
                dbtags.append(Phototag(event=event, tag=t))
            Phototag.objects.filter(event=event).delete()
            Phototag.objects.bulk_create(dbtags)
            logger.info('{} tags processed for {} ({})'.format(len(tags), event, event.id))
        thisresponse = {'event': str(event),
                        'numtags': len(tags),
                        'photos_scanned': len(photos),
                        'delta': len(tags) - len(oldtags),
                       }
        response['events'].append(thisresponse)
    response['result'] = 'success'
    response['message'] = 'thank you, come again!'
    return response


def get_event_photos(event):
    photos = []
    photos_page1 = flickr.photos.search(user_id=runwaterloo_flickr_id,
                                        tag_mode='all',
                                        tags='{}{}{}'.format(event.date.year,
                                                             event.race.slug,
                                                             event.distance.slug),
                                        per_page=photos_per_page,
                                        extras='tags')
    numpages = int(photos_page1['photos']['pages'])
    photos_page1 = photos_page1['photos']['photo']
    photos += photos_page1
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
        photos += photos_pageX['photos']['photo']
    return photos


def get_tags(photos, event):
    bib2member = get_bib2member(event)
    member2bib = get_member2bib(event)
    tags = []
    alltags2add = []
    for p in photos:
        pictags = p['tags'].split()
        ntags = [x for x in pictags if x.isdigit()]
        mtags = [x for x in pictags if x[0] == 'm']
        tags += ntags
        tags += mtags
        tags2add = []
        for n in ntags:                                                                 
            if n in bib2member:                                                         
                mtag = 'm{}'.format(bib2member[n])                                      
                if mtag not in mtags:                                                   
                    tags2add.append(mtag)                                               
                    mtags.append(mtag)                                                  
            if n in member2bib:                                                         
                bib = member2bib[n]                                                     
                if bib not in ntags:                                                    
                    tags2add.append(bib) 
        for m in mtags:
            if m in member2bib:
                bib = member2bib[m]
                if bib not in ntags:
                    tags2add.append(bib)
        if len(tags2add) > 0:
            strtags = ' '.join(tags2add)
            #tags += tags2add   #uncomment (DON'T DELETE) for prod
            alltags2add.append([p['id'], strtags]) 
    for i in alltags2add:
        logger.info(str(i))
        #newtags = flickr.photos.addtags(photo_id=i[0], tags=i[1])    #uncomment for prod
        #newtags = flickr.photos.addtags(photo_id='32921973080', tags='c9 c0')
        #for t in newtags['tags']['tag']:
        #    logger.info('New tag: event={} photo_id={} tag_content={} tag_id={}'.format(event.id, '32921973080', t['_content'], t['full_tag_id']))
    tags = sorted(set(tags))
    return tags


def get_bib2member(event):  
    bib2member = {}
    membersinrace = []
    membership = view_shared.get_membership(event=event)
    results = Result.objects.filter(event=event)
    for r in results:
        member = view_shared.get_member(r, membership)
        if member:
            bib2member[r.bib] = member.id
            membersinrace.append(member.id)
    if event.date > date(2017, 2, 12):
        membersasof = Member.objects.filter(active=True, joindate__lte=event.date).values_list('id', flat=True)
        for m in membersasof:
            if m in membersinrace:
                bib2member[m] = m
    return bib2member

                
def get_member2bib(event):
    member2bib = {}
    membership = view_shared.get_membership(event=event, include_inactive=True)
    results = Result.objects.filter(event=event)
    for r in results:
        member = view_shared.get_member(r, membership)
        if member:
            member2bib['m{}'.format(member.id)] = r.bib
            if event.date > date(2017, 2, 12):
                if member.joindate <= event.date:
                    member2bib[member.id] = r.bib
    return member2bib
