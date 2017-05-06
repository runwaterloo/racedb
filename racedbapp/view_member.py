from django.shortcuts import render
from itertools import chain
from collections import namedtuple
from .models import *
from . import utils
from datetime import date, timedelta
from operator import attrgetter

named_result = namedtuple('nr', ['result',
                                 'guntime',
                                 'gender_place',
                                 'category_place',
                                 'chiptime',
                                ]
                         )
named_pb = namedtuple('npb', ['time', 'event'])
named_badge = namedtuple('nb', ['name', 'date', 'image', 'url'])

def index(request, member_slug):
    member = Rwmember.objects.get(slug=member_slug, active=True)
    dbresults = (Result.objects
                 .select_related()
                 .filter(rwmember=member)
                 .exclude(place__gte=990000)
                 .order_by('-event__date')
                )
    total_distance = 0
    results = []
    best_gender_place = best_category_place = ''
    for r in dbresults:
        guntime = r.guntime - timedelta(microseconds=r.guntime.microseconds)
        chiptime = ''
        if r.chiptime:
            chiptime = (r.chiptime - 
                        timedelta(microseconds=r.chiptime.microseconds))
        gender_place = (Result.objects
                        .filter(event=r.event,
                                gender=r.gender,
                                place__lte=r.place
                               )
                        .count()
                       )
        category_place = ''
        if r.category.name != '':
            category_place = (Result.objects
                              .filter(event=r.event,
                                      category=r.category,
                                      place__lte=r.place)
                              .count()
                             )
        results.append(named_result(r,
                                    guntime,
                                    gender_place,
                                    category_place,
                                    chiptime)
                      )
        total_distance += r.event.distance.km
    fivek_pb = get_pb(results, '5-km')
    tenk_pb = get_pb(results, '10-km')
    results_with_gender_place = sorted([x for x in results
                                        if x.gender_place != '' ],
                                        key=attrgetter('gender_place')
                                      )
    if len(results_with_gender_place) > 0:
        best_gender_place = results_with_gender_place[0]
    results_with_category_place = sorted([x for x in results
                                          if x.category_place != '' ],
                                          key=attrgetter('category_place')
                                        )
    if len(results_with_category_place) > 0:
        best_category_place = results_with_category_place[0]
    total_distance = round(total_distance, 1)
    racing_since = ''
    if len(results) > 0:
        racing_since = results[-1].result.event.date.year
    badges = get_badges(member, results)
    context = {
               'member': member,
               'results': results,
               'total_distance': total_distance,
               'racing_since': racing_since,
               'fivek_pb': fivek_pb,
               'tenk_pb': tenk_pb,
               'best_gender_place': best_gender_place,
               'best_category_place': best_category_place,
               'badges': badges,
              }
    return render(request, 'racedbapp/member.html', context)

def get_pb(results, distance_slug):
    pb = ''
    pb_results = [x for x in results
                  if x.result.event.distance.slug == distance_slug ]
    if len(pb_results) > 0:
        pb = sorted(pb_results, key=attrgetter('result.guntime'))[0]
    return pb

def get_badges(member, results):
    badges = []
    badges += get_founders_badge(member)
    badges += get_total_kms_badge(results)
    #badges += get_wc_finishes_badge(results)
    badges += get_inaugural_finishes_badges(results)
    #badges += get_bow_finishes_badges(member, results)
    #badges += get_endurrun_finishes_badges(member, results)
    #badges += get_pb_badges(member, results)
    #badges += get_race_win_badges(results)
    #badges += get_endurrace_combined_badge(results)
    #badges += get_event_finishes_badge(results)
    #badges += get_adventurer_badge(results)
    badges = sorted(badges, key=attrgetter('date'), reverse=True)
    return badges

def get_founders_badge(member):
    FOUNDER_DATE = date(2017, 6, 18)
    founders_badge = []
    badge_image = 'https://foundersbrewing.com/wp-content/uploads/2015/06/centennial_ipa_badge_-920x920.png'
    if member.joindate <= FOUNDER_DATE:
        founders_badge.append(named_badge('Founding Member',
                              member.joindate,
                              'founding-member.png',
                              False))
    return founders_badge

def get_total_kms_badge(results):
    KMS_THRESHOLDS = [2000, 1000, 500, 250, 100]
    total_kms_badge = []
    total_kms = 0
    kms_date = []
    for r in reversed(results):
        total_kms += r.result.event.distance.km
        kms_date.append([total_kms, r.result.event.date])
    for i in KMS_THRESHOLDS:
        if total_kms >= i:
            for k in reversed(kms_date):
                if k[0] >= i:
                    date_earned = k[1]
                else:
                    break
            image = 'km-{}.png'.format(i)
            total_kms_badge.append(named_badge('Raced {} Total Kilometres'.format(i),
                                               date_earned,
                                               image,
                                               False))
            break
    return total_kms_badge

def get_wc_finishes_badge(results):
    WC_THRESHOLDS = [40, 20, 10, 5]
    wc_finishes_badge = []
    wc_finishes = [ x for x in results if x.result.event.race.slug == 'waterloo-classic' ]
    for i in WC_THRESHOLDS:
        if len(wc_finishes) >= i:
            date_earned = wc_finishes[-i].result.event.date
            wc_finishes_badge.append(named_badge('{} Waterloo Classic Finishes'.format(i),
                                                 date_earned,
                                                 'http://www.leanteen.com/file/pic/badge/2013/04/208a3b0d3903f47a96476d2c95e182d3.png',
                                                 False))
            break
    return wc_finishes_badge

def get_inaugural_finishes_badges(results):
    inaugural_finishes_badges = []
    current_race_ids = Samerace.objects.values_list('current_race_id', flat=True)
    old_race_ids = Samerace.objects.values_list('old_race_id', flat=True)
    races = Race.objects.exclude(id__in=current_race_ids)
    race_inaugural_years = {}
    for race in races:
        first_year = Event.objects.filter(race=race).aggregate(min_date=Min('date'))['min_date'].year
        race_inaugural_years[race] = first_year
    already_have = []
    for r in reversed(results):
        if r.result.event.race in race_inaugural_years:
          if r.result.event.date.year == race_inaugural_years[r.result.event.race]:
              if r.result.event.race not in already_have:
                  race = r.result.event.race
                  if race.id in old_race_ids:
                      race = Samerace.objects.get(old_race_id=race.id).current_race
                  image = 'inaugural-{}.png'.format(race.slug)
                  inaugural_finishes_badges.append(named_badge('Finished inaugural Run Waterloo event',
                                                   r.result.event.date,
                                                   image, 
                                                   False))
    return inaugural_finishes_badges

def get_bow_finishes_badges(member, results):
    bow_finishes_badges = []
    member_names = [member.name, ]
    if member.altname != '':
        member_names.append(member.altname)
    bowathletes = Bowathlete.objects.filter(name__in=member_names)
    if len(bowathletes) > 0:
        result_ids = [ x.result.event.id for x in results ]
    for b in bowathletes:
        event_ids = eval(Bow.objects.filter(id=b.bow_id).values_list('events', flat=True)[0])
        if set(event_ids).issubset(result_ids):
            last_date = Event.objects.get(id=event_ids[-1]).date
            bow = Bow.objects.get(id=b.bow_id)
            bow_finishes_badges.append(named_badge('{} Finisher'.format(bow.name), last_date, 'http://vignette1.wikia.nocookie.net/steamtradingcards/images/e/ed/Napoleon_Total_War_Badge_France.png/revision/latest?cb=20130823233645', False))
    return bow_finishes_badges

def get_endurrun_finishes_badges(member, results):
    endurrun_finishes_badges = []
    member_names = [member.name, ]
    if member.altname != '':
        member_names.append(member.altname)
    endurathletes = Endurathlete.objects.filter(name__in=member_names).order_by('year')
    sport_finishes = 0
    ultimate_finishes = 0
    if len(endurathletes) > 0:
        result_ids = [ x.result.event.id for x in results ]
    for e in endurathletes:
        division = e.division
        last_three_ids = Event.objects.select_related().filter(race__slug='endurrun',
                                         date__icontains=e.year,
                                         distance__slug__in=['25_5-km',
                                                             '10-km',
                                                             'marathon']).values_list('id', flat=True)
        if e.division.lower() == 'sport':
            event_ids = list(last_three_ids)
            if set(event_ids).issubset(result_ids):
                sport_finishes += 1
                sport_date_earned = Event.objects.get(id=event_ids[-1]).date
        elif e.division.lower() == 'ultimate':
            first_four_ids = Event.objects.select_related().filter(race__slug='endurrun',
                                 date__icontains=e.year,
                                 distance__slug__in=['half-marthon',
                                                     '15-km',
                                                     '30-km',
                                                     '10-mi']).values_list('id', flat=True)
            event_ids = list(first_four_ids) + list(last_three_ids)
            if set(event_ids).issubset(result_ids):
                ultimate_finishes += 1
                ultimate_date_earned = Event.objects.get(id=event_ids[-1]).date
    # uncomment this part to enable ENDURrun Sport finishes
    #if sport_finishes > 0:
    #    plural = ''
    #    if sport_finishes > 1:
    #        plural = 'es'
    #    endurrun_finishes_badges.append(named_badge('{} ENDURrun Sport Finish{}'.format(sport_finishes, plural), sport_date_earned, 'https://www.trophysupermarket.com/media/catalog/product/cache/1/small_image/260x/9df78eab33525d08d6e5fb8d27136e95/B/D/BDG-VC-3_2_1.jpg', False))
    if ultimate_finishes > 0:
        plural = ''
        if ultimate_finishes > 1:
            plural = 'es'
        endurrun_finishes_badges.append(named_badge('{} ENDURrun Ultimate Finish{}'.format(ultimate_finishes, plural), ultimate_date_earned, 'http://www.symbolarts.com/wp-content/uploads/2010/12/glenco-star-badge.png', False))
    return endurrun_finishes_badges

def get_pb_badges(member, results):
    pb_badges = []
    if member.gender == 'F':
        FIVEK_THRESHOLDS = [17, 18, 20, 22, 25]
        TENK_THRESHOLDS = [35, 37, 41, 45, 50]
    else:
        FIVEK_THRESHOLDS = [15, 16, 18, 20, 25]
        TENK_THRESHOLDS = [31, 33, 37, 41, 50]
    fivek_minutegroup = False
    fivek_pb = False
    tenk_minutegroup = False
    tenk_pb = False
    for r in reversed(results):
        # uncomment this to enable 5K time badge
        #if r.result.event.distance.slug == '5-km':
        #    if not fivek_pb:
        #        fivek_minutegroup = get_minutegroup(r.result, FIVEK_THRESHOLDS)
        #        fivek_pb = r.result
        #    else:
        #        if r.result.guntime < fivek_pb.guntime:
        #            new_minutegroup = get_minutegroup(r.result, FIVEK_THRESHOLDS)
        #            if fivek_minutegroup:
        #                if new_minutegroup < fivek_minutegroup:
        #                    fivek_minutegroup = new_minutegroup
        #                    fivek_pb = r.result
        #            else:
        #                fivek_pb = r.result
        #                fivek_minutegroup = new_minutegroup
        if r.result.event.distance.slug == '10-km':
            if not tenk_pb:
                tenk_minutegroup = get_minutegroup(r.result, TENK_THRESHOLDS)
                tenk_pb = r.result
            else:
                if r.result.guntime < tenk_pb.guntime:
                    new_minutegroup = get_minutegroup(r.result, TENK_THRESHOLDS)
                    if tenk_minutegroup:
                        if new_minutegroup < tenk_minutegroup:
                            tenk_minutegroup = new_minutegroup
                            tenk_pb = r.result
                    else:
                        tenk_pb = r.result
                        tenk_minutegroup = new_minutegroup
    if fivek_minutegroup:
        if member.gender == 'F':
            pb_badges.append(named_badge('Sub {} 5K Club'.format(fivek_minutegroup), fivek_pb.event.date, 'http://wonderville_media.s3.amazonaws.com/quiz%2Fquiz_images%2FCheetah.png', False))
        else:
            pb_badges.append(named_badge('Sub {} 5K Club'.format(fivek_minutegroup), fivek_pb.event.date, 'https://cdn.kastatic.org/images/badges/earth/work-horse-512x512.png', False))
    if tenk_minutegroup:
        if member.gender == 'F':
            pb_badges.append(named_badge('Sub {} 10K Club'.format(tenk_minutegroup), tenk_pb.event.date, 'http://i.ebayimg.com/images/g/ZMcAAMXQVERSytWa/s-l300.jpg', False))
        else:
            pb_badges.append(named_badge('Sub {} 10K Club'.format(tenk_minutegroup), tenk_pb.event.date, 'http://i.ebayimg.com/images/g/wdkAAOSw-jhUAcjD/s-l300.jpg', False))
    return pb_badges

def get_race_win_badges(results):
    race_win_badges = []
    races_won = []
    image = 'http://www.lightsgoout.co.uk/wp-content/lgouploadedmedia/badges1-300x300.jpg'
    wins = [x for x in reversed(results) if x.gender_place == 1]
    for w in wins:
        thisrace = w.result.event.race
        if len(Samerace.objects.filter(old_race_id=thisrace.id)) == 1:
            new_race_id = Samerace.objects.get(old_race_id=thisrace.id).current_race_id
            thisrace = Race.objects.get(id=new_race_id)
        if thisrace not in races_won:
            stage = ''
            if thisrace.slug == 'endurrun':
                stage= 'Stage '
            race_win_badges.append(named_badge('{} {}Winner'.format(thisrace.name, stage),
                                   w.result.event.date,
                                   image,
                                   False))
            races_won.append(thisrace)
    return race_win_badges

# Future use
def get_endurrace_combined_badge(results):
    endurrace_combined_badge = []
    endurrace_5k_years = []
    endurrace_count = 0
    for r in reversed(results):
        if r.result.event.race.slug == 'endurrace':
            if r.result.event.distance.slug == '5-km':
                endurrace_5k_years.append(r.result.event.date.year)
            elif r.result.event.distance.slug == '8-km':
                if r.result.event.date.year in endurrace_5k_years:
                    date_earned = r.result.event.date
                    endurrace_count += 1
    if endurrace_count > 0:
        plural = ''
        if endurrace_count > 1:
            plural = 'es'
        endurrace_combined_badge.append(named_badge('{} ENDURrace Combined Finish{}'.format(endurrace_count, plural), date_earned, 'http://us.123rf.com/450wm/blueringmedia/blueringmedia1607/blueringmedia160700183/59362745-relay-running-icon-on-round-badge-illustration.jpg?ver=6', False))
    return endurrace_combined_badge

# Fture use
def get_event_finishes_badge(results):
    EVENT_THRESHOLDS = [200, 100, 50, 25, 10, 1]
    event_finishes_badge = []
    for i in EVENT_THRESHOLDS:
        if len(results) >= i:
            plural = ''
            if i > 1:
                plural = 'es'
            date_earned = results[-i].result.event.date
            event_finishes_badge.append(named_badge('{} Event Finish{}'.format(i, plural), date_earned, 'https://www.edx.org/sites/default/files/upload/pbaruah-edx-verified-badge.png', False))
            break
    return event_finishes_badge

# Future use
def get_adventurer_badge(results):
    ADVENTURER_THRESHOLD = 10
    adventurer_badge = []
    same_races_dict = dict(Samerace.objects.values_list('old_race_id', 'current_race_id'))
    race_finishes = []
    race_finishes_dates = []
    for r in reversed(results):
        thisrace_id = r.result.event.race.id
        if thisrace_id in same_races_dict:
            thisrace_id = same_races_dict[thisrace_id]
        if thisrace_id not in race_finishes:
            race_finishes.append(thisrace_id)
            race_finishes_dates.append(r.result.event.date)
    if len(race_finishes) >= ADVENTURER_THRESHOLD:
        date_earned = race_finishes_dates[ADVENTURER_THRESHOLD - 1]
        adventurer_badge.append(named_badge('Adventurer ({} Difference Races)'.format(ADVENTURER_THRESHOLD), date_earned, 'https://members.scouts.org.uk/images/badges/sc-cs-adch.png', False))
    return adventurer_badge

def get_minutegroup(result, thresholds):
    thisminutegroup = False
    for t in thresholds:
        if result.guntime.seconds < t * 60:
            thisminutegroup = t
            break
    return thisminutegroup
