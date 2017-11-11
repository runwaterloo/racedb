#!/usr/bin/env python
""" parseresults.py - Race result parsing utility. """
from django.core.management.base import BaseCommand, CommandError
from racedbapp.models import * 
from racedbapp import view_shared
import os
import datetime
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import sys
import logging
logger = logging.getLogger(__name__)

MASTERS_SUBSTRINGS = ['40-', '45-', '50-', '55-', '60-', '65-',
                      '70-', '75-', '40+', '50+', '60+', '70+', 'MST',
                      '4049', '5059', '6069']

class Command(BaseCommand):
    help = 'Adds races to database from pre'

    def add_arguments(self, parser):
        parser.add_argument('-e',
        action='store',
        dest='event',
        default=False,
        help='Scrape specific event')

    def handle(self, *args, **options):
        premodified = Config.objects.get(name='premodified')
        races = Race.objects.values_list('prename', flat=True)
        page_size = 10
        events = []
        done = False
        if options['event']:
            resultsurl = 'http://pre.scrw.ca/api/events/{}'.format(options['event'])
            r = requests.get(resultsurl, verify=False)
            result = r.json()
            events.insert(0, result)
        else:
            resultsurl = 'http://pre.scrw.ca/api/events/?limit={}'.format(page_size)
            while True:
                r = requests.get(resultsurl, verify=False)
                pageresults = r.json()['results']
                for result in pageresults:
                    modified = result['modified']
                    if modified > premodified.value:
                        events.insert(0, result)
                    else:
                        done = True
                if done:
                    break
                if r.json()['next']:
                    resultsurl = r.json()['next']
                else:
                    break
        if len(events) == 0:
            info = 'No updated races found'
            logger.info(info)
        endurrace_years = []
        for event in events:
            year = event['date'][0:4]
            if event['race'] in races and 'roadraceresults' not in event['resultsurl']:
                race = Race.objects.get(prename=event['race'])
                distance = Distance.objects.get(prename=event['distance'])
                dohill = False
                splits = []
                if race.slug == 'baden-road-races':
                    if distance.slug == '7-mi':
                        dohill = True
                        hill_results = []
                flickrsetid = None
                youtube_id = ''
                youtube_offset_seconds = None
                if len(Event.objects.filter(id=event['id'])) == 1:
                    flickrsetid = Event.objects.get(id=event['id']).flickrsetid
                    youtube_id =  Event.objects.get(id=event['id']).youtube_id
                    youtube_offset_seconds = Event.objects.get(id=event['id']).youtube_offset_seconds
                e = Event(id = event['id'],
                          race = race,
                          distance = distance,
                          date = event['date'],
                          city = event['city'],
                          resultsurl = event['resultsurl'],
                          flickrsetid = flickrsetid,
                          youtube_id = youtube_id,
                          youtube_offset_seconds = youtube_offset_seconds)
                e.save()
                membership = view_shared.get_membership(event=e, include_inactive=True)
                page_size = 500
                results = []
                resultsurl = ('http://pre.scrw.ca/api/results/?event={}&limit={}'
                              .format(event['id'], page_size))
                gun_equal_chip = True
                while True:
                    r = requests.get(resultsurl, verify=False)
                    pageresults = r.json()['results']
                    for result in pageresults:
                        extra_dict = {}
                        if result['extra'] != '':
                            extra_dict = eval(result['extra'])
                        resultcategory = result['category']
                        try:
                            category = Category.objects.get(name=resultcategory)
                        except:
                            ismasters = False
                            for i in MASTERS_SUBSTRINGS:
                                if i in resultcategory:
                                    ismasters = True
                            category = Category(name=resultcategory,
                                                ismasters=ismasters)
                            category.save()
                        guntime = maketimedelta(result['guntime'])
                        chiptime = maketimedelta(result['chiptime'])
                        if guntime != chiptime:
                            gun_equal_chip = False
                        age = result['age']
                        try:
                            int(age)
                        except:
                            age = None
                        division = ''
                        if 'division' in extra_dict:
                            division = extra_dict['division']
                        member = get_member(event, result, membership)
                        newresult = Result(event_id = event['id'],
                                           place = result['place'],
                                           bib = result['bib'],
                                           athlete = result['athlete'],
                                           gender = result['gender'],
                                           category = category,
                                           city = result['city'],
                                           chiptime = chiptime,
                                           guntime = guntime,
                                           age = age,
                                           division = division,
                                           rwmember = member)
                        results.append(newresult)
                        splits = add_splits(event, result, extra_dict, splits)
                        if 'division' in extra_dict:
                            process_endurathlete(event, result, extra_dict)
                        if 'relay_team' in extra_dict:
                            process_endurteam(event, result, extra_dict)
                        if dohill:
                            if result['extra'] != '':
                                raw_hill_time = eval(result['extra'])['Hill Time']
                                hill_time = maketimedelta(raw_hill_time)  
                                newhillresult = Prime(event_id=event['id'],
                                                      place=result['place'],
                                                      gender=result['gender'],
                                                      time=hill_time)
                                hill_results.append(newhillresult)
                    if r.json()['next']:
                        resultsurl = r.json()['next']
                    else:
                        break
                # Process results
                Result.objects.filter(event_id=event['id']).delete()
                for result in results:
                    if gun_equal_chip:
                        result.chiptime = None
                    result.save()
                if race.slug == 'endurrace':
                    endurrace_years.append(e.date[0:4])
                info = ('{} results processed for {} {} {} (Event {})'
                        .format(len(results), year, race.name,
                        distance.name, event['id']))
                logger.info(info)
                
                # Process splits
                Split.objects.filter(event_id=event['id']).delete()
                if len(splits) > 0:
                    Split.objects.bulk_create(splits)
                    info = ('{} splits processed for {} {} {} (Event {})'
                            .format(len(splits), year, race.name,
                            distance.name, event['id']))
                    logger.info(info)

                # Process hills
                if dohill:
                    Prime.objects.filter(event_id=event['id']).delete()
                    for hillresult in hill_results:
                        hillresult.save()
                    info = ('{} hill results processed for {} {} {} (Event {})'
                            .format(len(hill_results), year, race.name,
                            distance.name, event['id']))
                    logger.info(info)

                teamresults = []
                teamresultsurl = ('http://pre.scrw.ca/api/teamresults/?event={}&page_size={}'
                              .format(event['id'], page_size))
                while True:
                    r = requests.get(teamresultsurl, verify=False)
                    pageresults = r.json()['results']
                    for result in pageresults:
                        team_category_id = Teamcategory.objects.get(name=result['team_category']).id
                        athlete_time = maketimedelta(result['athlete_time'])
                        newteamresult = Teamresult(event_id = event['id'],
                                                   team_category_id = team_category_id,
                                                   team_place = result['team_place'],
                                                   team_name = result['team_name'],
                                                   athlete_team_place = result['athlete_team_place'],
                                                   athlete_time = athlete_time,
                                                   athlete_name = result['athlete_name'],
                                                   counts = result['counts'],
                                                   estimated = result['estimated'])
                        teamresults.append(newteamresult)
                    if r.json()['next']:
                        teamresultsurl = r.json()['next']
                    else:
                        break
                # Delete any existing team results for this event
                Teamresult.objects.filter(event_id=event['id']).delete()
                for teamresult in teamresults:
                    teamresult.save()
                info = ('{} team results processed for {} {} {} (Event {})'
                        .format(len(teamresults), year, race.name,
                        distance.name, event['id']))
                logger.info(info)
            else:
                info = ('{} {} {} (Event {}) not part of this series, skipping'
                        .format(year, event['race'], event['distance'], event['id']))
                logger.info(info)
            premodified.value = event['modified']
            premodified.save()                 
        if len(endurrace_years) > 0:
            process_endurrace(set(endurrace_years))

def maketimedelta(strtime):
    if '.' in strtime:                                                     
        microsec = strtime.split('.')[1]                                      
        if int(microsec) == 0:
            milliseconds = 0
        else:
            if microsec[0] == 0:
                milliseconds = int(microsec) / 10000
            else:
                milliseconds= int(microsec) / 1000
        hours, minutes, seconds = strtime.split('.')[0].split(':')        
    else:                                                                    
        milliseconds = 0                                                     
        hours, minutes, seconds = strtime.split(':')                       
        if ' ' in hours:
            daypart, hourpart = hours.split(' ')
            hours = 24 * int(daypart) + int(hourpart)
    timedelta = datetime.timedelta(hours=int(hours),
                                   minutes=int(minutes),
                                   seconds=int(seconds), 
                                   milliseconds=milliseconds)
    return timedelta

def process_endurrace(years):
    info = 'Processing ENDURrace for years: {}'.format(years)
    logger.info(info)
    race = Race.objects.get(slug='endurrace')
    fivek_distance = Distance.objects.get(slug='5-km')
    eightk_distance = Distance.objects.get(slug='8-km')
    for year in years:
        results = []
        fivek_results = Result.objects.filter(event__race=race,
                                              event__distance=fivek_distance,
                                              event__date__icontains=year)
        eightk_results = Result.objects.filter(event__race=race,
                                               event__distance=eightk_distance,
                                               event__date__icontains=year)
        if len(fivek_results) == 0 or len(eightk_results) == 0:
            continue
        fivek_dict = {}
        eightk_dict = {}
        for result in fivek_results:
            fivek_dict[result.athlete] = result
        for result in eightk_results:
            eightk_dict[result.athlete] = result
        for k, v in fivek_dict.items():
            if k in eightk_dict:
                guntime = v.guntime + eightk_dict[k].guntime
                this_result = Endurraceresult(year=year,
                                              category=v.category,
                                              athlete=v.athlete,
                                              gender=v.gender,
                                              city=v.city,
                                              bib=v.bib,
                                              guntime=guntime,
                                              fivektime=v.guntime,
                                              eightktime=eightk_dict[k].guntime)
                results.append(this_result)
        Endurraceresult.objects.filter(year=year).delete()
        Endurraceresult.objects.bulk_create(results)
        info = 'Processed {} ENDURrace results for {}.'.format(len(results), year)
        logger.info(info)

def add_splits(event, result, extra_dict, splits):
    ### Add any splits ###
    for k, v in extra_dict.items():
        if 'split' not in k:
            continue
        split_num = int(k.strip('split'))
        split_time = maketimedelta(v)
        this_split = Split(event_id = event['id'],
                           place = result['place'],
                           split_num = split_num,
                           split_time = split_time)
        splits.append(this_split)
    return splits

def process_endurathlete(event, result, extra_dict):
    division = extra_dict['division']
    if division in ('Ultimate', 'Sport'):
        year = int(event['date'][0:4])
        name = result['athlete']
        gender = result['gender']
        try:
            age = int(result['age'])
        except:
            age = None
        city = result['city']
        province = country = ''
        if 'province' in extra_dict:
            province = extra_dict['province']
        if 'country' in extra_dict:
            country = extra_dict['country']
        try:
            ea = Endurathlete.objects.get(year=year, division=division, name=name)
        except:
            ea = Endurathlete(year=year,
                              division=division,
                              name=name,
                              gender=gender,
                              age=age,
                              city=city,
                              province=province,
                              country=country)
            ea.save()
        else:
            if age:
                if ea.age:
                    if age < ea.age:
                        ea.age = age
                else:
                    ea.age = age
            if city != '':
                ea.city = city
            if province != '':
                ea.province = province
            if country != '':
                ea.country = country
            ea.save()

def process_endurteam(event, result, extra_dict):
    year = int(event['date'][0:4])
    name = extra_dict['relay_team']
    athlete = result['athlete']
    athlete_gender = result['gender']
    try:
        age = int(result['age'])
    except:
        age = None
    distance = event['distance']
    try:
        et = Endurteam.objects.get(year=year, name=name)
    except:
        ismasters = False
        if age:
            if age >= 40:
                ismasters = True
        et = Endurteam(year=year,
                       name=name,
                       gender=athlete_gender,
                       ismasters=ismasters)
    else:
        if et.gender == 'M':
            if athlete_gender == 'F':
                et.gender = 'X'
        elif et.gender == 'F':
            if athlete_gender == 'M':
                et.gender = 'X'
        if et.ismasters:
            if not age:
                et.ismasters = False
            else:
                if age < 40:
                    et.ismasters = False
    if distance == 'Half Marathon':
        et.st1 = athlete
    elif distance == '15K':
        et.st2 = athlete
    elif distance == '30K':
        et.st3 = athlete
    elif distance == '10M':
        et.st4 = athlete
    elif distance == '25.6K':
        et.st5 = athlete
    elif distance == '10K':
        et.st6 = athlete
    elif distance == 'Marathon':
        et.st7 = athlete
    et.save()

    
def get_member(event, result, membership):
    member = None
    lower_athlete = result['athlete'].lower()                                       
    if lower_athlete in membership.names:                                        
        member = membership.names[lower_athlete]                                 
    if '{}-{}'.format(event['id'], result['place']) in membership.includes:     
        member = membership.includes['{}-{}'.format(event['id'], result['place'])]
    if member:                                                                   
        if '{}-{}'.format(event['id'], result['place']) in membership.excludes: 
            if member in membership.excludes['{}-{}'.format(event['id'], result['place'])]:
                member = None
    return member
