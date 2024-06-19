from collections import namedtuple
from datetime import date, timedelta
from operator import attrgetter

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min
from django.shortcuts import redirect, render

from . import view_boost
from .shared import utils
from .models import Bow, Bowathlete, Config, Event, Race, Result, Rwmember, Samerace

named_result = namedtuple(
    "nr", ["result", "guntime", "gender_place", "category_place", "chiptime"]
)
named_pb = namedtuple("npb", ["time", "event"])
named_badge = namedtuple("nb", ["name", "date", "image", "url"])


def index(request, member_slug):
    try:
        member = Rwmember.objects.get(slug=member_slug, active=True)
    except:
        return redirect("/members/")
    results, total_distance = get_memberresults(member)
    fivek_pb = get_pb(results, "5-km")
    tenk_pb = get_pb(results, "10-km")
    results_with_gender_place = sorted(
        [x for x in results if x.gender_place != ""], key=attrgetter("gender_place")
    )
    best_gender_place = best_category_place = ""
    if len(results_with_gender_place) > 0:
        best_gender_place = results_with_gender_place[0]
    results_with_category_place = sorted(
        [x for x in results if x.category_place != ""], key=attrgetter("category_place")
    )
    if len(results_with_category_place) > 0:
        best_category_place = results_with_category_place[0]
    total_distance = round(total_distance, 1)
    racing_since = ""
    if len(results) > 0:
        racing_since = results[-1].result.event.date.year
    badges = get_badges(member, results)
    try:
        nophoto_url = Config.objects.get(name="nophoto_url").value
    except ObjectDoesNotExist:
        nophoto_url = ""
    if member.gender in ("M", "F"):
        boost = get_boost(member, request)
    else:
        boost = False
    no_profile_camera = False
    if "no-profile-camera" in [x.name for x in member.tags.all()]:
        no_profile_camera = True
    context = {
        "member": member,
        "results": results,
        "total_distance": total_distance,
        "racing_since": racing_since,
        "fivek_pb": fivek_pb,
        "tenk_pb": tenk_pb,
        "best_gender_place": best_gender_place,
        "best_category_place": best_category_place,
        "badges": badges,
        "nophoto_url": nophoto_url,
        "boost": boost,
        "no_profile_camera": no_profile_camera,
    }
    return render(request, "racedbapp/member.html", context)


def get_pb(results, distance_slug):
    pb = ""
    pb_results = [
        x
        for x in results
        if x.result.event.distance.slug == distance_slug
        and x.result.event.race.id != 17
    ]
    if len(pb_results) > 0:
        pb = sorted(pb_results, key=attrgetter("result.guntime"))[0]
    return pb


def get_badges(member, results):
    badges = []
    badges += get_founders_badge(member)
    badges += get_total_kms_badge(results)
    badges += get_wc_finishes_badge(results)
    badges += get_inaugural_finishes_badges(results)
    badges += get_bow_finishes_badges(member, results)
    badges += get_endurrun_finishes_badges(member, results)
    badges += get_pb_badges(member, results)
    badges += get_race_win_badges(results)
    badges += get_endurrace_combined_badge(results)
    # badges += get_event_finishes_badge(results)
    # badges += get_adventurer_badge(results)
    badges = sorted(badges, key=attrgetter("date", "name"), reverse=True)
    return badges


def get_founders_badge(member):
    FOUNDER_DATE = date(2017, 6, 18)
    founders_badge = []
    if member.joindate <= FOUNDER_DATE:
        founders_badge.append(
            named_badge(
                "Founding Member", member.joindate, "founding-member.png", False
            )
        )
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
            image = "km-{}.png".format(i)
            total_kms_badge.append(
                named_badge(
                    "Raced {} Total Kilometres".format(i), date_earned, image, False
                )
            )
            break
    return total_kms_badge


def get_wc_finishes_badge(results):
    WC_THRESHOLDS = [40, 20, 10, 5]
    wc_finishes = [x for x in results if x.result.event.race.slug == "waterloo-classic"]
    wc_finishes_years = []
    wc_finishes_dates = []
    wc_finishes_badge = []
    for i in wc_finishes:
        if i.result.event.date.year not in wc_finishes_years:
            wc_finishes_years.append(i.result.event.date.year)
            wc_finishes_dates.append(i.result.event.date)
    for i in WC_THRESHOLDS:
        if len(wc_finishes_dates) >= i:
            date_earned = wc_finishes_dates[-i]
            image = "waterloo-classic-finisher-{}.png".format(i)
            wc_finishes_badge.append(
                named_badge(
                    "Waterloo Classic {} Time Finisher".format(i),
                    date_earned,
                    image,
                    False,
                )
            )
            break
    return wc_finishes_badge


def get_inaugural_finishes_badges(results):
    inaugural_finishes_badges = []
    current_race_ids = Samerace.objects.values_list("current_race_id", flat=True)
    old_race_ids = Samerace.objects.values_list("old_race_id", flat=True)
    races = Race.objects.exclude(id__in=current_race_ids)
    race_inaugural_years = {}
    for race in races:
        first_year = (
            Event.objects.filter(race=race)
            .aggregate(min_date=Min("date"))["min_date"]
            .year
        )
        race_inaugural_years[race] = first_year
    already_have = []
    for r in reversed(results):
        if r.result.event.race in race_inaugural_years:
            if r.result.event.date.year == race_inaugural_years[r.result.event.race]:
                race = r.result.event.race
                if race.id in old_race_ids:
                    race = Samerace.objects.get(old_race_id=race.id).current_race
                if r.result.event.race not in already_have:
                    image = utils.get_achievement_image(race.slug, "inaugural")
                    inaugural_finishes_badges.append(
                        named_badge(
                            "Finished inaugural {}".format(race.name),
                            r.result.event.date,
                            image,
                            False,
                        )
                    )
                    already_have.append(race)
    return inaugural_finishes_badges


def get_bow_finishes_badges(member, results):
    bow_finishes_badges = []
    member_names = [member.name]
    if member.altname != "":
        member_names.append(member.altname)
    bowathletes = Bowathlete.objects.filter(name__in=member_names)
    if len(bowathletes) > 0:
        result_ids = [x.result.event.id for x in results]
    for b in bowathletes:
        event_ids = eval(
            Bow.objects.filter(id=b.bow_id).values_list("events", flat=True)[0]
        )
        if set(event_ids).issubset(result_ids):
            last_date = Event.objects.get(id=event_ids[-1]).date
            bow = Bow.objects.get(id=b.bow_id)
            bow_longname = bow.name.replace("BOW", "Battle of Waterloo")
            bow_num = bow.slug.split("-")[1]
            image = "bow-finisher-{}.png".format(bow_num)
            bow_finishes_badges.append(
                named_badge("{} Finisher".format(bow_longname), last_date, image, False)
            )
    return bow_finishes_badges


def get_endurrun_finishes_badges(member, results):
    endurrun_finishes_badges = []
    years = []
    yearsdict = {}
    ultimate_finishes = 0
    endurrun_results = [
        x for x in reversed(results) if x.result.event.race.slug == "endurrun"
    ]
    for er in endurrun_results:
        years.append(er.result.event.date.year)
        if er.result.event.date.year in yearsdict:
            yearsdict[er.result.event.date.year].append(er)
        else:
            yearsdict[er.result.event.date.year] = [er]
    for year in sorted(set(years)):
        if len(yearsdict[year]) == 7:
            ultimate_finishes += 1
            ultimate_date_earned = yearsdict[year][6].result.event.date
    if ultimate_finishes > 0:
        ULTIMATE_THRESHOLDS = [10, 5, 2, 1]
        for i in ULTIMATE_THRESHOLDS:
            if ultimate_finishes >= i:
                break
        image = "endurrun-ultimate-finisher-{}.png".format(i)
        endurrun_finishes_badges.append(
            named_badge(
                "ENDURrun Ultimate {} Time Finisher".format(ultimate_finishes),
                ultimate_date_earned,
                image,
                False,
            )
        )
    return endurrun_finishes_badges


def get_pb_badges(member, results):
    pb_badges = []
    if member.gender == "F":
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
        if r.result.event.distance.slug == "5-km":
            if r.result.event.race.id == 17:
                continue
            if not fivek_pb:
                fivek_minutegroup = get_minutegroup(r.result, FIVEK_THRESHOLDS)
                fivek_pb = r.result
            else:
                if r.result.guntime < fivek_pb.guntime:
                    new_minutegroup = get_minutegroup(r.result, FIVEK_THRESHOLDS)
                    if fivek_minutegroup:
                        if new_minutegroup < fivek_minutegroup:
                            fivek_minutegroup = new_minutegroup
                            fivek_pb = r.result
                    else:
                        fivek_pb = r.result
                        fivek_minutegroup = new_minutegroup
        if r.result.event.distance.slug == "10-km":
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
        image = "5-km-{}-{}.png".format(fivek_minutegroup, member.gender.lower())
        pb_badges.append(
            named_badge(
                "5 KM: Sub {} Club".format(fivek_minutegroup),
                fivek_pb.event.date,
                image,
                False,
            )
        )
    if tenk_minutegroup:
        image = "10-km-{}-{}.png".format(tenk_minutegroup, member.gender.lower())
        pb_badges.append(
            named_badge(
                "10 KM: Sub {} Club".format(tenk_minutegroup),
                tenk_pb.event.date,
                image,
                False,
            )
        )
    return pb_badges


def get_race_win_badges(results):
    race_win_badges = []
    races_won = []
    wins = [x for x in reversed(results) if x.gender_place == 1]
    for w in wins:
        thisrace = w.result.event.race
        if len(Samerace.objects.filter(old_race_id=thisrace.id)) == 1:
            new_race_id = Samerace.objects.get(old_race_id=thisrace.id).current_race_id
            thisrace = Race.objects.get(id=new_race_id)
        if thisrace not in races_won:
            image = utils.get_achievement_image(thisrace.slug, "event-winner")
            race_win_badges.append(
                named_badge(
                    "Won an overall event at {}".format(thisrace.name),
                    w.result.event.date,
                    image,
                    False,
                )
            )
            races_won.append(thisrace)
    return race_win_badges


def get_endurrace_combined_badge(results):
    EC_THRESHOLDS = [10, 5, 2, 1]
    endurrace_combined_badge = []
    endurrace_5k_years = []
    endurrace_count = 0
    for r in reversed(results):
        if r.result.event.race.slug == "endurrace":
            if r.result.event.distance.slug == "5-km":
                endurrace_5k_years.append(r.result.event.date.year)
            elif r.result.event.distance.slug == "8-km":
                if r.result.event.date.year in endurrace_5k_years:
                    date_earned = r.result.event.date
                    endurrace_count += 1
    for i in EC_THRESHOLDS:
        if endurrace_count >= i:
            image = "endurrace-combined-finisher-{}.png".format(i)
            endurrace_combined_badge.append(
                named_badge(
                    "ENDURrace Combined {} Time Finisher".format(endurrace_count),
                    date_earned,
                    image,
                    False,
                )
            )
            break
    return endurrace_combined_badge


# Fture use
def get_event_finishes_badge(results):
    EVENT_THRESHOLDS = [200, 100, 50, 25, 10, 1]
    event_finishes_badge = []
    for i in EVENT_THRESHOLDS:
        if len(results) >= i:
            plural = ""
            if i > 1:
                plural = "es"
            date_earned = results[-i].result.event.date
            event_finishes_badge.append(
                named_badge(
                    "{} Event Finish{}".format(i, plural),
                    date_earned,
                    "https://www.edx.org/sites/default/files/upload/pbaruah-edx-verified-badge.png",
                    False,
                )
            )
            break
    return event_finishes_badge


def get_adventurer_badge(results):
    ADVENTURER_THRESHOLD = 10
    adventurer_badge = []
    same_races_dict = dict(
        Samerace.objects.values_list("old_race_id", "current_race_id")
    )
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
        adventurer_badge.append(
            named_badge(
                "Finished {} or more different timed races".format(
                    ADVENTURER_THRESHOLD
                ),
                date_earned,
                "adventurer.png",
                False,
            )
        )
    return adventurer_badge


def get_minutegroup(result, thresholds):
    thisminutegroup = False
    for t in thresholds:
        if result.guntime.seconds < t * 60:
            thisminutegroup = t
            break
    return thisminutegroup


def get_memberresults(member):
    results = []
    total_distance = 0
    dbresults = (
        Result.objects.select_related()
        .filter(rwmember=member)
        .exclude(place__gte=990000)
        .order_by("-event__date", "-event__distance__km")
    )
    total_distance = 0
    for r in dbresults:
        guntime = r.guntime - timedelta(microseconds=r.guntime.microseconds)
        chiptime = ""
        if r.chiptime:
            chiptime = r.chiptime - timedelta(microseconds=r.chiptime.microseconds)
        gender_place = Result.objects.filter(
            event=r.event, gender=r.gender, place__lte=r.place
        ).count()
        category_place = ""
        if r.category.name != "":
            category_place = Result.objects.filter(
                event=r.event, category=r.category, place__lte=r.place
            ).count()
        results.append(named_result(r, guntime, gender_place, category_place, chiptime))
        total_distance += r.event.distance.km
    return results, total_distance


def get_boost(member, request):
    boost = []
    boost_years = get_boost_years(member)
    for boost_year in boost_years:
        boost_year_standings = view_boost.index(
            request, boost_year, standings_only=True
        )
        member_boost_standings = [
            x for x in boost_year_standings if x.member_id == member.id
        ]
        if member_boost_standings:
            boost.append(member_boost_standings[0])
    return boost


def get_boost_years(member):
    boost_years = []
    for tag in member.tags.all():
        if tag.name.startswith("boost"):
            try:
                boost_year = int(tag.name.split("-")[1])
            except Exception:
                continue
            else:
                boost_years.append(boost_year)
    return sorted(boost_years, reverse=True)
