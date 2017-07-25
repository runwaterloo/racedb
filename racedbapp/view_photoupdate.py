from django.http import HttpResponse, Http404
from django.shortcuts import render
from collections import namedtuple
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
    qsdate = validate(request)
    events = get_events(qsdate)
    numevents = len(events)
    if numevents == 0:
        logger.warning('No events found for {}'.format(qsdate))
        results = []
    else:
        results = update_event_tags(events)
    context = { 'numevents' : numevents,
                'results' : results,
              }
    return render(request, 'racedbapp/photoupdate.html', context)


def get_events(qsdate):
    """
    Determine which events should processed based on the date value given in
    the qstring. There are two simple cases:
        
    1) 'all': process ALL events, this is slow and not recommended
    2) a valid date: process events for the given date only
    
    In an effort to distribute the workload things get considerably more
    complicated when the third case, 'auto', is provided. In this case it will
    always process events that occured in the past 31 days, and it may include
    additional events depending on the hour of day that this job is running.
    In hours 6-23 it only includes events from the past 31 days, but hours 0-5
    will add:
    
    1) Events older than 31 days but not older than 730 days with a month
       matching code for that hour. For example, hour 2 adds events that
       occurred in June or July.
    
    2) Events older than 730 days with a day (day of month) matching the
       current day of month, and a year where the remainder of dividing the
       year by 6 is 0.

    This job is scheduled in cron hourly and the the point of all this
    complexity is to distribute the extra event processing throughout the 
    night so that no single run has too much work, the following criteria are
    met:

    1) All events in the past month are processed hourly
    
    2) All events in the past two years are processed daily

    3) All other events are processed monthly on the anniversary of their
       day of month
    """
    if qsdate == 'all':
        events = Event.objects.all().exclude(flickrsetid=None)
    elif qsdate == 'auto':
        now = datetime.now()
        today = date.today()
        hour = now.hour
        day = now.day
        month = now.month
        month_ago = today - timedelta(days=31)
        two_years_ago = today - timedelta(days=730)
        events = list(Event.objects.filter(date__gte=month_ago).exclude(flickrsetid=None))
        if hour in range(6):
            months = {0: (1, 2, 3),
                      1: (4, 5),
                      2: (6, 7),
                      3: (8,),
                      4: (9, 10),
                      5: (11,12)}
            logger.info('Auto checking events past month, past two years {}, anniversary day (batch {})'.format(months[hour], hour))
            past_two_years_events = list(Event.objects.filter(date__lt=month_ago, date__gte=two_years_ago, date__month__in=months[hour]).exclude(flickrsetid=None))
            all_anniversary_events = Event.objects.filter(date__lt=two_years_ago, date__day=day).exclude(flickrsetid=None)
            anniversary_events = [x for x in all_anniversary_events if x.date.year % 6 == hour]
            events = events + past_two_years_events + anniversary_events
        else:
            logger.info('Auto checking events past month')
    else:
        events = list(Event.objects.filter(date=qsdate).exclude(flickrsetid=None))
    return events


def update_event_tags(events):
    named_result = namedtuple('nr', ['event',
                                     'numphotos',
                                     'finishers',
                                     'unique_tags',
                                     'pct',
                                     'delta',
                                     'tags_applied'])
    results = []
    logger.info('Starting photo tag update for {} events'.format(len(events)))
    for event in events:
        logger.info('Starting photo tag update for {} ({})'.format(event, event.id))
        photos = get_event_photos(event)
        tags, tags_applied = do_tags(photos, event)
        event_bibs = Result.objects.filter(event=event).values_list('bib', flat=True)
        all_ntags = [x for x in tags if x.isdigit()]
        event_ntags = [x for x in all_ntags if x in event_bibs]
        mtagnums = [x.lstrip('m') for x in tags if ismtag(x)]
        oldtags = Phototag.objects.filter(event=event).values_list('tag', flat=True)
        if len(tags) == 0:
            logger.info('No tags found for {} ({}). No changes made.'.format(event, event.id))
        elif list(event_ntags) == list(oldtags):
            logger.info('{} tags unchanged for {} ({})'.format(len(event_ntags), event, event.id))
        else:
            dbtags = []
            for t in event_ntags:
                dbtags.append(Phototag(event=event, tag=t))
            Phototag.objects.filter(event=event).delete()
            Phototag.objects.bulk_create(dbtags)
            logger.info('{} tags processed for {} ({})'.format(len(event_ntags), event, event.id))
        nophotomembers = list(Rwmember.objects.filter(active=True, hasphotos=False).values_list('id', flat=True))
        for m in mtagnums:
            if int(m) in nophotomembers:
                member =  Rwmember.objects.get(id=m)
                member.hasphotos = True
                member.save()
                logger.info('Set hasphotos to true for member {} ({})'.format(member, m))
        results.append(named_result(event,
                                    len(photos),
                                    len(event_bibs),
                                    len(event_ntags),
                                    '{:.1%}'.format(len(event_ntags) / len(event_bibs)),
                                    len(event_ntags) - len(oldtags),
                                    tags_applied))
    return results


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


def do_tags(photos, event):
    bib2member = get_bib2member(event)
    member2bib = get_member2bib(event)
    tags = []
    alltags2add = []
    for p in photos:
        pictags = p['tags'].split()
        ntags = [x for x in pictags if x.isdigit()]
        mtags = [x for x in pictags if ismtag(x)]
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
                    ntags.append(bib)
        for m in mtags:
            if m in member2bib:
                bib = member2bib[m]
                if bib not in ntags:
                    tags2add.append(bib)
        if len(tags2add) > 0:
            strtags = ' '.join(tags2add)
            tags += tags2add
            alltags2add.append([p['id'], strtags]) 
    for i in alltags2add:
        try:
            newtags = flickr.photos.addtags(photo_id=i[0], tags=i[1])
        except Exception as e:
            logger.error('Unable to add tags to https://www.flickr.com/photos/runwaterloo/{}/'.format(i[0]))
            logger.error('flickrapi.exceptions.FlickrError: {}'.format(e))
        else:
            for t in newtags['tags']['tag']:
                logger.info('New tag: event={} photo_id={} tag_content={} tag_id={}'.format(event.id, i[0], t['_content'], t['full_tag_id']))
    tags = sorted(set(tags))
    return tags, len(alltags2add)


def get_bib2member(event):  
    bib2member = {}
    membership = view_shared.get_membership(event=event)
    member_assumption = get_member_assumption(event)
    results = Result.objects.filter(event=event)
    for r in results:
        member = view_shared.get_member(r, membership)
        if member:
            bib2member[r.bib] = member.id
    if member_assumption:
        membersasof = Rwmember.objects.filter(active=True, joindate__lte=event.date).values_list('id', flat=True)
        for m in membersasof:
            bib2member[str(m)] = m
    return bib2member

                
def get_member2bib(event):
    member2bib = {}
    membership = view_shared.get_membership(event=event, include_inactive=True)
    member_assumption = get_member_assumption(event)
    results = Result.objects.filter(event=event)
    for r in results:
        member = view_shared.get_member(r, membership)
        if member:
            member2bib['m{}'.format(member.id)] = r.bib
            if member_assumption:
                if member.joindate <= event.date:
                    member2bib[str(member.id)] = r.bib
    return member2bib


def get_member_assumption(event):
    """
    Determine if we should assume that number tags matching a member id
    can only belong to that member. This should only be done AFTER
    2017-02-12 (Re-Fridgee-Eighther) because before that regular bibs will
    conflict with member ids, and it should not be done for ENDURrun because
    member bibs should not be worn.
    """
    no_assumption_races = ('endurrun',)
    no_assumption_events = (819,)
    member_assumption = False
    if event.date > date(2017, 4, 1):
        if event.race.slug not in no_assumption_races:
            if event.id not in no_assumption_events:
                member_assumption = True
    return member_assumption


def ismtag(tag):
    """ 
    Check if a tag is a valid mtag. This means that
    it starts with an m and the rest is a number.
    """
    ismtag = False
    if tag[0] == 'm':
        if tag.lstrip('m').isdigit():
            ismtag = True
    return ismtag


def validate(request):
    """
    Validate that the request has everything it needs and return the date
    """

    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    notifykey = Config.objects.filter(name='notifykey')[0].value
    if 'notifykey' not in qstring:
        logger.warning('missing key')
        raise Http404('Parameter "notifykey" not in URL')
    elif qstring['notifykey'][0] != notifykey:
        logger.warning('invalid key')
        raise Http404('Invalid key')
    elif 'date' not in qstring:
        logger.warning('missing date')
        raise Http404('Parameter "date" not in URL')
    else:
        qsdate = qstring['date'][0]
    if qsdate not in ('auto', 'all'):
        try:
            datetime.strptime(qsdate, '%Y-%m-%d')
        except ValueError:
            logger.warning('invalid date format')
            raise Http404('Invalid date format, should be YYYY-MM-DD')
    return qsdate
