from django.shortcuts import render
from django.http import Http404
#from django.db.models import Count
from urllib import parse
from collections import namedtuple
from .models import *
from . import view_shared, utils
#from django.http import HttpResponse
from django.db.models import Count, Max, Q
from datetime import timedelta
from operator import attrgetter
#import datetime

named_filter = namedtuple('nf', ['current', 'choices'])                       
named_choice = namedtuple('nc', ['name', 'url'])                              
named_split = namedtuple('ns', ['split_num', 'split_time'])

def index(request, year, race_slug, distance_slug):
    qstring = parse.parse_qs(request.META['QUERY_STRING'])
    page = get_page(qstring)
    category = get_category(qstring)
    division = get_division(qstring)
    try:
        event = Event.objects.select_related().get(race__slug=race_slug,
                                                   distance__slug=distance_slug,
                                                   date__icontains=year)
    except:
        raise Http404('Matching event not found'.format(division))
    races = view_shared.create_samerace_list(event.race)
    team_categories = get_team_categories(event)
    hill_dict = get_hill_dict(event)
    dbphototags = list(Phototag.objects.filter(event=event).values_list('tag', flat=True))
    phototags = [x for x in dbphototags if x.isdigit()]
    event_flickr_str = '{}-{}-{}'.format(event.date.year, event.race.slug, event.distance.slug).replace('-','').replace('_','')
    wheelchair_results = Wheelchairresult.objects.filter(event=event)
    pages = get_pages(event, page, hill_dict,
                      wheelchair_results, team_categories) 
    year_filter = get_year_filter(event, races)
    distance_filter = get_distance_filter(event, races)
    category_filter = get_category_filter(event, category, division)
    division_filter = get_division_filter(event, division, category)
    if page == 'Wheelchair':
        all_results = Wheelchairresult.objects.filter(event=event)
        hasage = False
    else:
        all_results = Result.objects.select_related().filter(event=event)
        hasage = all_results.hasage(event)
    results, max_splits = get_results(event, all_results, page, category, division, hill_dict, phototags)
    split_headings = []
    for i in range(1, max_splits+1):
        split_headings.append('Split {}'.format(i))
    hasdivision = False
    if event.race.slug == 'endurrun':
        hasdivision = True
    extra_name = get_extra_name(event)
    context = {
               'event': event,
               'page': page,
               'pages': pages,
               'year_filter': year_filter,
               'distance_filter': distance_filter,
               'category_filter': category_filter,
               'division_filter': division_filter,
               'results': results,
               'hasage': hasage,
               'hasdivision': hasdivision,
               'hill_dict': hill_dict,
               'split_headings': split_headings,
               'extra_name': extra_name,
               'phototags': phototags,
               'event_flickr_str': event_flickr_str,
              }
    return render(request, 'racedbapp/event.html', context)

def get_masters(event, division):
    masters = []
    all_masters = Result.objects.filter(event=event).filter(Q(category__ismasters=True) | Q(age__gte=40))
    if division != 'All':
        all_masters = all_masters.filter(division=division)
    masters_count = all_masters.count()
    if masters_count > 0:
        masters.append({'category__name': 'Masters', 'count': masters_count})
        female_masters_count = all_masters.filter(gender='F').count()
        if female_masters_count > 0:
            masters.append({'category__name': 'F-Masters', 'count': female_masters_count})
        male_masters_count = all_masters.filter(gender='M').count()
        if male_masters_count > 0:
            masters.append({'category__name': 'M-Masters', 'count': male_masters_count})
    return masters

def get_genders(event, division):
    all_results = Result.objects.filter(event=event)
    if division != 'All':
        all_results = all_results.filter(division=division)
    abbr_genders = all_results.exclude(gender='').values('gender').order_by('gender').annotate(count=Count('gender')).order_by('gender')
    genders = []
    for i in abbr_genders:
        if i['gender'] == 'F':
            genders.append({'category__name': 'Female', 'count': i['count']})
        elif i['gender'] == 'M':
            genders.append({'category__name': 'Male', 'count': i['count']})
    return genders

def get_categories(event, division):
    all_results = Result.objects.filter(event=event)
    if division != 'All':
        all_results = all_results.filter(division=division)
    categories = all_results.exclude(category__name='').values('category__name').order_by('category').annotate(count=Count('category__name')).order_by('category__name')
    return categories

def get_divisions(event, category):
    all_results = Result.objects.filter(event=event)
    if category != 'All':
        if category in ('Female', 'Male'):
            all_results = all_results.filter(gender=category[0])
        elif category == 'Masters':
            all_results = all_results.filter(Q(category__ismasters=True) | Q(age__gte=40))
        elif category == 'F-Masters':
            all_results = all_results.filter(gender='F').filter(Q(category__ismasters=True) | Q(age__gte=40))
        elif category == 'M-Masters':
            all_results = all_results.filter(gender='M').filter(Q(category__ismasters=True) | Q(age__gte=40))
        else:
            all_results = all_results.filter(category__name=category)
    divisions = all_results.exclude(division='').values('division').order_by('division').annotate(count=Count('division')).order_by('-division')
    return divisions
    
def get_hill_dict(event):                                                        
    hill_dict = False                                                            
    if event.race.slug == 'baden-road-races':                                    
        if event.distance.slug == '7-mi':                                        
            hill_results = Prime.objects.filter(event=event)                     
            hill_dict = {}                                                       
            for r in hill_results:                                               
                hill_dict[r.place] = r.time                                      
    return hill_dict          

def get_page(qstring):
    page = 'Overall'
    if 'hill' in qstring:
        page = 'Hill Sprint'
    elif 'wheelchair' in qstring:
        page = 'Wheelchair'
    return page

def get_category(qstring):
    category = 'All'
    if 'filter' in qstring:
        category = qstring['filter'][0]
    return category

def get_division(qstring):
    division = 'All'
    if 'division' in qstring:
        division = qstring['division'][0]
        if division not in ('Ultimate', 'Sport', 'Relay', 'Guest'):
            raise Http404('Division "{}" is not valid'.format(division))
    return division

def get_pages(event, page, hill_dict, wheelchair_results, team_categories):
    named_page = namedtuple('np', ('active', 'href', 'label'))
    pages = []
    if page == 'Overall':
        pages.append(named_page('active', '#', 'Overall'))
    else:
        pages.append(named_page
                     ('inactive',
                      '/event/{}/{}/{}/'.format(event.date.year,
                                                event.race.slug,
                                                event.distance.slug),
                      'Overall'))
    if hill_dict:
        if page == 'Hill Sprint':
            pages.append(named_page('active', '#', 'Hill Sprint'))
        else:
            pages.append(named_page
                         ('inactive',
                          '/event/{}/{}/{}/?hill=true'.format(event.date.year,
                                                               event.race.slug,
                                                               event.distance.slug),
                          'Hill Sprint'))
    if wheelchair_results.count() > 0:
        if page == 'Wheelchair':
            pages.append(named_page('active', '#', 'Wheelchair'))
        else:
            pages.append(named_page
                         ('inactive',
                          '/event/{}/{}/{}/?wheelchair=true'.format(event.date.year,
                                                                     event.race.slug,
                                                                     event.distance.slug),
                          'Wheelchair'))
    for tc in team_categories:
        pages.append(named_page
                         ('inactive',
                          '/event/{}/{}/{}/team/{}'.format(event.date.year,
                                                            event.race.slug,
                                                            event.distance.slug,
                                                            tc.slug),
                          tc.name))
    return pages

def get_team_categories(event):
    present_team_categories = Teamresult.objects.filter(event=event).values_list('team_category__name', flat=True)
    present_team_categories = set(sorted(present_team_categories))               
    team_categories = Teamcategory.objects.filter(name__in=present_team_categories)
    return team_categories

def get_distance_filter(event, races):
    distance_ids = Result.objects.filter(event__race__in=races, event__date__icontains=event.date.year).values_list('event__distance', flat=True)
    distances = Distance.objects.filter(pk__in=set(distance_ids)).order_by('-km')
    choices = []
    for d in distances:
        if d == event.distance:
            continue
        choices.append(named_choice(d.name, '/event/{}/{}/{}/'.format(event.date.year, event.race.slug, d.slug)))
    distance_filter = named_filter(event.distance.name, choices)
    return distance_filter

def get_year_filter(event, races):
    rawresults = Result.objects.select_related().filter(event__race__in=races, event__distance=event.distance)
    dates = rawresults.order_by('-event__date').values_list('event__date', 'event__race__slug').distinct()
    choices = []
    for d in dates:
        year = d[0].year
        if year == event.date.year:
            continue
        choices.append(named_choice(year, '/event/{}/{}/{}/'.format(year, d[1], event.distance.slug)))
    year_filter = named_filter(event.date.year, choices)
    return year_filter

def get_category_filter(event, category, division):
    all_results = Result.objects.filter(event=event)
    if division != 'All':
        all_results = all_results.filter(division=division)
    total_count = all_results.count()
    genders = get_genders(event, division)
    masters = get_masters(event, division)
    categories = get_categories(event, division)
    all_categories = genders + masters + list(categories)
    choices = []
    if category == 'All':
        current = 'All ({})'.format(total_count)
    else:
        try:
            category_count = [ x['count'] for x in all_categories if x['category__name'] == category ][0]
        except:
            category_count = 0
        current = '{} ({})'.format(category, category_count)
        if division == 'All':
            choices.append(named_choice('All ({})'.format(total_count), '/event/{}/{}/{}/'.format(event.date.year, event.race.slug, event.distance.slug)))
        else:
            choices.append(named_choice('All ({})'.format(total_count), '/event/{}/{}/{}/?division={}'.format(event.date.year, event.race.slug, event.distance.slug, division)))
    for a in all_categories:
        if a['category__name'] == category:
            continue
        clean_category = a['category__name'].replace('+','%2B')
        if division == 'All':
            choices.append(named_choice('{} ({})'.format(a['category__name'], a['count']), '/event/{}/{}/{}/?filter={}'.format(event.date.year, event.race.slug, event.distance.slug, clean_category)))
        else:
            choices.append(named_choice('{} ({})'.format(a['category__name'], a['count']), '/event/{}/{}/{}/?filter={}&division={}'.format(event.date.year, event.race.slug, event.distance.slug, clean_category, division)))
    category_filter = named_filter(current, choices)
    return category_filter

def get_division_filter(event, division, category):
    divisions = get_divisions(event, category)
    if len(divisions) == 0:
        division_filter = False
    else:
        all_results = Result.objects.filter(event=event)
        if category != 'All':
            if category in ('Female', 'Male'):
                all_results = all_results.filter(gender=category[0])
            elif category == 'Masters':
                all_results = all_results.filter(Q(category__ismasters=True) | Q(age__gte=40))
            elif category == 'F-Masters':
                all_results = all_results.filter(gender='F').filter(Q(category__ismasters=True) | Q(age__gte=40))
            elif category == 'M-Masters':
                all_results = all_results.filter(gender='M').filter(Q(category__ismasters=True) | Q(age__gte=40))
            else:
                all_results = all_results.filter(category__name=category)
        total_count = all_results.count()
        choices = []
        if division == 'All':
            current = 'All ({})'.format(total_count)
        else:
            try:
                division_count = [ x['count'] for x in divisions if x['division'] == division ][0]
            except:
                division_count = 0
            current = '{} ({})'.format(division, division_count)
            if category == 'All':
                choices.append(named_choice('All ({})'.format(total_count), '/event/{}/{}/{}/'.format(event.date.year, event.race.slug, event.distance.slug)))
            else:
                choices.append(named_choice('All ({})'.format(total_count), '/event/{}/{}/{}/?filter={}'.format(event.date.year, event.race.slug, event.distance.slug, category)))
        for d in divisions:
            if d['division'] == division:
                continue
            if category == 'All':
                choices.append(named_choice('{} ({})'.format(d['division'], d['count']), '/event/{}/{}/{}/?division={}'.format(event.date.year, event.race.slug, event.distance.slug, d['division'])))
            else:
                choices.append(named_choice('{} ({})'.format(d['division'], d['count']), '/event/{}/{}/{}/?filter={}&division={}'.format(event.date.year, event.race.slug, event.distance.slug,category, d['division'])))
        division_filter = named_filter(current, choices)
    return division_filter

def get_results(event, all_results, page, category, division, hill_dict, phototags):
    named_result = namedtuple('nr', 
                     [
                      'place',
                      'bib',
                      'name',
                      'relay_team',
                      'gender',
                      'gender_place',
                      'category',
                      'category_place',
                      'age',
                      'division',
                      'guntime',
                      'prime',
                      'chiptime',
                      'city',
                      'ismasters',
                      'splits',
                      'member',
                      'hasphotos',
                      'youtube_url',
                     ])
    results = []
    relay_dict = get_relay_dict(event)
    gender_place_dict = {'F': 0, 'M': 0}
    category_place_dict = {}
    haschiptime = False

    event_splits = Split.objects.filter(event=event)
    splits_list = event_splits.values_list('place', 'split_num', 'split_time')
    splits_dict = dict([((a, b), c) for a, b, c in splits_list])
    max_splits = False
    if event_splits:
        max_splits = int(event_splits.aggregate(Max('split_num'))['split_num__max'])
    membership = view_shared.get_membership(event=event)
    has_youtube = False
    if event.youtube_id and event.youtube_offset_seconds:
        has_youtube = True
        LEAD_TIME_SECONDS = 7
    for r in all_results:
        relay_team = False
        if r.gender == 'F':
            gender_place_dict['F'] += 1
            gender_place = gender_place_dict['F']
        elif r.gender == 'M':
            gender_place_dict['M'] += 1
            gender_place = gender_place_dict['M']
        category_place = ''
        if r.category.name != '':
            if r.category.name in category_place_dict:
                category_place_dict[r.category.name] += 1
                category_place = category_place_dict[r.category.name] 
            else:
                category_place_dict[r.category.name] = 1
                category_place = 1
        if r.athlete in relay_dict:
            relay_team = relay_dict[r.athlete]
        age = ''
        if page != 'Wheelchair':
            if r.age:
                age = r.age
        guntime = chiptime = ''
        if r.place < 990000:
            guntime = r.guntime - timedelta(microseconds=r.guntime.microseconds)
            if r.chiptime:
                chiptime = r.chiptime - timedelta(microseconds=r.chiptime.microseconds)
        try:
            prime = hill_dict[r.place]
        except:
            prime = ''
        else:
            prime = get_short_time(prime)
        ismasters = False
        if r.category.ismasters:
            ismasters = True
        else:
            if page != 'Wheelchair':
                if r.age:
                    if r.age >= 40:
                        ismasters = True
        if page == 'Wheelchair':
            result_division = ''
        else:
            result_division = r.division
        splits = []
        if event_splits:
            for i in range(1, max_splits+1):
                try:
                    splits.append(named_split(i, get_short_time(splits_dict[(r.place, i)])))
                except:
                    splits.append(named_split(i, ''))
        member = view_shared.get_member(r, membership)
        hasphotos = False
        youtube_url = False
        if has_youtube and r.place < 990000:
            video_position_seconds = (guntime.total_seconds()
                                      - event.youtube_offset_seconds 
                                      - LEAD_TIME_SECONDS)
            minutes = int(video_position_seconds // 60)
            seconds = int(video_position_seconds % 60)
            video_position = '{}m{}s'.format(minutes, seconds)
            youtube_url = 'https://youtu.be/{}?t={}'.format(event.youtube_id,
                                                            video_position)
        if r.bib in phototags:
            hasphotos = True
        results.append(named_result(r.place,
                                    r.bib,
                                    r.athlete,
                                    relay_team,
                                    r.gender,
                                    gender_place,
                                    r.category.name,
                                    category_place,
                                    age,
                                    result_division,
                                    guntime,
                                    prime,
                                    chiptime,
                                    r.city,
                                    ismasters,
                                    splits,
                                    member,
                                    hasphotos,
                                    youtube_url
                                   ))
    results = filter_results(results, category, division)
    if page == 'Hill Sprint':
        results = get_hill_results(results, named_result)
    return results, max_splits

def get_relay_dict(event):
    relay_dict = {}
    if event.race.slug == 'endurrun':
        if event.distance.slug == 'half-marathon':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st1', 'name'))
        if event.distance.slug == '15-km':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st2', 'name'))
        if event.distance.slug == '30-km':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st3', 'name'))
        if event.distance.slug == '10-mi':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st4', 'name'))
        if event.distance.slug == '25_6-km':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st5', 'name'))
        if event.distance.slug == '10-km':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st6', 'name'))
        if event.distance.slug == 'marathon':
            relay_dict = dict(Endurteam.objects.filter(year=event.date.year).values_list('st7', 'name'))
    return relay_dict

def get_short_time(orig_time):
    short_time = str(orig_time).lstrip('0:')
    return short_time

def filter_results(results, category, division):
    if category == 'Female':
        results = [ x for x in results if x.gender == 'F' ]
    elif category == 'Male':
        results = [ x for x in results if x.gender == 'M' ]
    elif category == 'Masters':
        results = [ x for x in results if x.ismasters ]
    elif category == 'F-Masters':
        results = [ x for x in results if x.ismasters and x.gender == 'F' ]
    elif category == 'M-Masters':
        results = [ x for x in results if x.ismasters and x.gender == 'M' ]
    elif category != 'All':
        results = [ x for x in results if x.category == category ]
    if division != 'All':
        results = [ x for x in results if x.division == division ]
    return results

def get_hill_results(results, named_result):
    hill_results = []
    results = [ x for x in results if x.prime != '' ]
    for i, r in enumerate(sorted(results, key=attrgetter('prime', 'place')), 1):
        hill_results.append(named_result(
           i,
           r.bib,
           r.name,
           r.relay_team,
           r.gender,
           r.gender_place,
           r.category,
           r.category_place,
           r.age,
           r.division,
           r.guntime,
           r.prime,
           r.chiptime,
           r.city,
           r.ismasters,
           r.splits,
           r.member,
           r.hasphotos,
           r.youtube_url,
           ))
    return hill_results

def get_extra_name(event):
    extra_name = ''
    if event.race.slug == 'endurrun':
        if event.distance.slug == 'half-marathon':
            extra_name = 'Stage 1 - '
        elif event.distance.slug == '15-km':
            extra_name = 'Stage 2 - '
        elif event.distance.slug == '30-km':
            extra_name = 'Stage 3 - '
        elif event.distance.slug == '10-mi':
            extra_name = 'Stage 4 - '
        elif event.distance.slug == '25_6-km':
            extra_name = 'Stage 5 - '
        elif event.distance.slug == '10-km':
            extra_name = 'Stage 6 - '
        elif event.distance.slug == 'marathon':
            extra_name = 'Stage 7 - '
    return extra_name
