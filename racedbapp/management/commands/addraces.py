#!/usr/bin/env python
""" parseresults.py - Race result parsing utility. """
import datetime
import logging

import gspread
import requests
from django.core.management.base import BaseCommand
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from racedbapp import tasks, view_shared
from racedbapp.models import (
    Category,
    Distance,
    Endurathlete,
    Endurraceresult,
    Endurteam,
    Event,
    Prime,
    Race,
    Relay,
    Result,
    Split,
    Teamcategory,
    Teamresult,
)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

MASTERS_SUBSTRINGS = [
    "40-",
    "45-",
    "50-",
    "55-",
    "60-",
    "65-",
    "70-",
    "75-",
    "40+",
    "50+",
    "60+",
    "70+",
    "MST",
    "4049",
    "5059",
    "6069",
]


class Command(BaseCommand):
    help = "Adds races to database from Google Sheets"

    def add_arguments(self, parser):
        parser.add_argument(
            "-e",
            action="store",
            dest="event_id",
            default=False,
            help="Scrape specific event",
        )

    def handle(self, *args, **options):
        events = []
        slack_results = []
        self.stdout.write("RRW UPDATE FROM GOOGLE SHEET TO RRW")
        if options["event_id"]:
            event_id = options["event_id"]
            self.stdout.write("Processing event_id: {}".format(event_id))
            events = Event.objects.filter(id=event_id)
        else:
            self.stdout.write("Processing all events for today")
            today = datetime.datetime.today()
            events = Event.objects.filter(date=today)
        self.stdout.write("Events:")
        for e in events:
            self.stdout.write("  {} (Event {})".format(e, e.id))
        if len(events) == 0:
            self.stdout.write("No events found to update")
            exit()
        endurrace_years = []
        self.stdout.write("Results:")
        for event in events:
            year = event.date.year
            gender_place_dict = {"F": 0, "M": 0}
            category_place_dict = {}
            race = Race.objects.get(slug=event.race.slug)
            distance = event.distance
            dohill = False
            splits = []
            relays = []
            if race.slug == "baden-road-races":
                if distance.slug == "7-mi":
                    dohill = True
                    hill_results = []
            membership = view_shared.get_membership(event=event, include_inactive=True)
            results = []
            gun_equal_chip = True
            if "docs.google.com" not in event.resultsurl:
                self.stdout.write(
                    "ERROR: Resuts URL for {} is not a google sheet".format(e)
                )
                return
            google_results = get_results_from_google(event.resultsurl)
            for result in google_results["individual"]:
                if "athlete" not in result:
                    result["athlete"] = result["name"]
                extra_dict = get_extra_dict(result)
                if "category" in result:
                    resultcategory = result["category"]
                else:
                    resultcategory = ""
                try:
                    category = Category.objects.get(name=resultcategory)
                except Exception:
                    ismasters = False
                    for i in MASTERS_SUBSTRINGS:
                        if i in resultcategory:
                            ismasters = True
                    category = Category(name=resultcategory, ismasters=ismasters)
                    category.save()
                guntime = maketimedelta(result["guntime"])
                if "chiptime" in result:
                    chiptime = maketimedelta(result["chiptime"])
                else:
                    chiptime = guntime
                if guntime != chiptime:
                    gun_equal_chip = False
                if "age" in result:
                    age = int(result["age"])
                else:
                    age = None
                division = ""
                if "division" in extra_dict:
                    division = extra_dict["division"]
                member = get_member(event, result, membership)
                gender_place = category_place = None
                if result["place"] < 990000:
                    if result["gender"] == "Male":
                        result["gender"] = "M"
                    if result["gender"] == "Female":
                        result["gender"] = "F"
                    if result["gender"] == "F":
                        gender_place_dict["F"] += 1
                        gender_place = gender_place_dict["F"]
                    elif result["gender"] == "M":
                        gender_place_dict["M"] += 1
                        gender_place = gender_place_dict["M"]
                    if category.name != "":
                        if category.name in category_place_dict:
                            category_place_dict[category.name] += 1
                            category_place = category_place_dict[category.name]
                        else:
                            category_place_dict[category.name] = 1
                            category_place = 1
                newresult = Result(
                    event_id=event.id,
                    place=result["place"],
                    bib=result["bib"],
                    athlete=result["athlete"],
                    gender=result["gender"],
                    category=category,
                    city=result.get("city", None),
                    chiptime=chiptime,
                    guntime=guntime,
                    age=age,
                    division=division,
                    rwmember=member,
                    gender_place=gender_place,
                    category_place=category_place,
                )
                results.append(newresult)
                splits = add_splits(event, result, extra_dict, splits)
                if "division" in extra_dict:
                    process_endurathlete(event, result, extra_dict)
                if "relay_team" in extra_dict:
                    if event.race.slug == "endurrun":
                        process_endurteam(event, result, extra_dict)
                    elif event.race.slug == "laurier-loop":
                        newrelayresult = Relay(
                            event_id=event.id,
                            place=result["place"],
                            relay_team=extra_dict["relay_team"],
                            relay_team_place=extra_dict["relay_team_place"],
                            relay_team_time=maketimedelta(
                                extra_dict["relay_team_time"]
                            ),
                            relay_leg=extra_dict["relay_leg"],
                        )
                        relays.append(newrelayresult)
                if dohill:
                    if result["extra"] != "":
                        if "Hill Time" in result["extra"]:
                            raw_hill_time = eval(result["extra"])["Hill Time"]
                            hill_time = maketimedelta(raw_hill_time)
                            newhillresult = Prime(
                                event_id=event.id,
                                place=result["place"],
                                gender=result["gender"],
                                time=hill_time,
                            )
                            hill_results.append(newhillresult)
            # Process results
            Result.objects.filter(event_id=event.id).delete()
            for result in results:
                if gun_equal_chip:
                    result.chiptime = None
                result.save()
            if race.slug == "endurrace":
                endurrace_years.append(event.date[0:4])
            info = "{} results processed for {} {} {} (Event {})".format(
                len(results), year, race.name, distance.name, event.id
            )
            logger.info(info)
            self.stdout.write("  {}".format(info))
            slack_results.append(info)

            # Process splits
            Split.objects.filter(event_id=event.id).delete()
            if len(splits) > 0:
                Split.objects.bulk_create(splits)
                info = "{} splits processed for {} {} {} (Event {})".format(
                    len(splits), year, race.name, distance.name, event.id
                )
                logger.info(info)
                self.stdout.write("  {}".format(info))
                slack_results.append(info)

            #         # Process relays  ## NOT IMPLEMENTED YET
            #         if len(relays) > 0:
            #             Relay.objects.filter(event_id=event.id).delete()
            #             Relay.objects.bulk_create(relays)
            #             info = "{} relay results processed for {} {} {} (Event {})".format(
            #                 len(relays), year, race.name, distance.name, event.id
            #             )
            #             logger.info(info)
            #             slack_results.append(info)

            # Process hills
            if dohill:
                Prime.objects.filter(event_id=event.id).delete()
                for hillresult in hill_results:
                    hillresult.save()
                info = "{} hill results processed for {} {} {} (Event {})".format(
                    len(hill_results), year, race.name, distance.name, event.id
                )
                logger.info(info)
                self.stdout.write("  {}".format(info))
                slack_results.append(info)

            # Process team results
            if google_results["team"]:
                teamresults = []
                for result in google_results["team"]:
                    team_category_id = Teamcategory.objects.get(
                        name=result["team_category"]
                    ).id
                    athlete_time = maketimedelta(result["athlete_time"])
                    if result["counts"] == "TRUE":
                        result_counts = True
                    else:
                        result_counts = False
                    if result["estimated"] == "TRUE":
                        result_estimated = True
                    else:
                        result_estimated = False
                    newteamresult = Teamresult(
                        event_id=event.id,
                        team_category_id=team_category_id,
                        team_place=result["team_place"],
                        team_name=result["team_name"],
                        athlete_team_place=result["athlete_team_place"],
                        athlete_time=athlete_time,
                        athlete_name=result["athlete_name"],
                        counts=result_counts,
                        estimated=result_estimated,
                    )
                    teamresults.append(newteamresult)
                # Delete any existing team results for this event
                Teamresult.objects.filter(event_id=event.id).delete()
                for teamresult in teamresults:
                    teamresult.save()
                info = "{} team results processed for {} {} {} (Event {})".format(
                    len(teamresults), year, race.name, distance.name, event.id
                )
                logger.info(info)
                self.stdout.write("  {}".format(info))
                if len(teamresults) > 0:
                    slack_results.append(info)

            # Process PBs
            info = "Processed PBs for {} ({})".format(event, event.id)
            logger.info(info)
            process_rwpbs(e)
        if len(endurrace_years) > 0:
            slack_results = process_endurrace(set(endurrace_years), slack_results)
        if len(slack_results) > 0:
            tasks.slack_results_update.delay(slack_results)
        info = "Clearing cache"
        logger.info(info)
        tasks.clear_cache.delay()
        info = "Process complete"
        logger.info(info)
        self.stdout.write("Process complete!")


def maketimedelta(strtime):
    if "." in strtime:
        microsec = strtime.split(".")[1]
        if int(microsec) == 0:
            milliseconds = 0
        else:
            if microsec[0] == 0:
                milliseconds = int(microsec) / 10000
            else:
                milliseconds = int(microsec) / 1000
        hours, minutes, seconds = strtime.split(".")[0].split(":")
    else:
        milliseconds = 0
        if len(strtime.split(":")) == 3:
            hours, minutes, seconds = strtime.split(":")
            if " " in hours:
                daypart, hourpart = hours.split(" ")
                hours = 24 * int(daypart) + int(hourpart)
        else:
            hours = 0
            minutes, seconds = strtime.split(":")
    timedelta = datetime.timedelta(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        milliseconds=milliseconds,
    )
    return timedelta


def process_endurrace(years, slack_results):
    info = "Processing ENDURrace for years: {}".format(years)
    logger.info(info)
    race = Race.objects.get(slug="endurrace")
    fivek_distance = Distance.objects.get(slug="5-km")
    eightk_distance = Distance.objects.get(slug="8-km")
    for year in years:
        results = []
        fivek_results = Result.objects.filter(
            event__race=race,
            event__distance=fivek_distance,
            event__date__icontains=year,
        )
        eightk_results = Result.objects.filter(
            event__race=race,
            event__distance=eightk_distance,
            event__date__icontains=year,
        )
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
                thiscategory = v.category

                # start 2019 override
                if result.event.date.year == 2019:
                    thiscategory = endurrace_category_fix(thiscategory)
                # end 2019 override

                this_result = Endurraceresult(
                    year=year,
                    category=thiscategory,
                    athlete=v.athlete,
                    gender=v.gender,
                    city=v.city,
                    bib=v.bib,
                    guntime=guntime,
                    fivektime=v.guntime,
                    eightktime=eightk_dict[k].guntime,
                )
                results.append(this_result)
        Endurraceresult.objects.filter(year=year).delete()
        Endurraceresult.objects.bulk_create(results)
        info = "{} ENDURrace combined results processed for {}".format(
            len(results), year
        )
        logger.info(info)
        slack_results.append(info)
        return slack_results


def endurrace_category_fix(curcategory):
    """Fix to override ENDURrace combined categories"""
    categoryname = curcategory.name
    categoryname = categoryname.replace("S", "B")
    categoryname = categoryname.replace("L", "B")
    categoryname = categoryname.replace("-12", "-19")
    categoryname = categoryname.replace("13-15", "-19")
    categoryname = categoryname.replace("16-19", "-19")
    try:
        category = Category.objects.get(name=categoryname)
    except Exception:
        ismasters = False
        for i in MASTERS_SUBSTRINGS:
            if i in categoryname:
                ismasters = True
        category = Category(name=categoryname, ismasters=ismasters)
        category.save()
    return category


def add_splits(event, result, extra_dict, splits):
    """Add any splits"""
    for k, v in extra_dict.items():
        if "split" not in k:
            continue
        split_num = int(k.strip("split"))
        if v == "":
            split_time = None
        else:
            split_time = maketimedelta(v)
        this_split = Split(
            event_id=event.id,
            place=result["place"],
            split_num=split_num,
            split_time=split_time,
        )
        splits.append(this_split)
    return splits


def process_endurathlete(event, result, extra_dict):
    division = extra_dict["division"]
    if division in ("Ultimate", "Sport"):
        year = int(event.date.year)
        name = result["athlete"]
        gender = result["gender"]
        try:
            age = int(result["age"])
        except Exception:
            age = None
        city = result["city"]
        province = country = ""
        if "province" in extra_dict:
            province = extra_dict["province"]
        if "country" in extra_dict:
            country = extra_dict["country"]
        try:
            ea = Endurathlete.objects.get(year=year, division=division, name=name)
        except Exception:
            ea = Endurathlete(
                year=year,
                division=division,
                name=name,
                gender=gender,
                age=age,
                city=city,
                province=province,
                country=country,
            )
            ea.save()
        else:
            if age:
                if ea.age:
                    if age < ea.age:
                        ea.age = age
                else:
                    ea.age = age
            if city != "":
                ea.city = city
            if province != "":
                ea.province = province
            if country != "":
                ea.country = country
            ea.save()


def process_endurteam(event, result, extra_dict):
    year = int(event.date.year)
    name = extra_dict["relay_team"]
    athlete = result["athlete"]
    athlete_gender = result["gender"]
    try:
        age = int(result["age"])
    except Exception:
        age = None
    distance = event.distance
    try:
        et = Endurteam.objects.get(year=year, name=name)
    except Exception:
        ismasters = False
        if age:
            if age >= 40:
                ismasters = True
        et = Endurteam(year=year, name=name, gender=athlete_gender, ismasters=ismasters)
    else:
        if et.gender == "M":
            if athlete_gender == "F":
                et.gender = "X"
        elif et.gender == "F":
            if athlete_gender == "M":
                et.gender = "X"
        if et.ismasters:
            if not age:
                et.ismasters = False
            else:
                if age < 40:
                    et.ismasters = False
    if distance == "Half Marathon":
        et.st1 = athlete
    elif distance == "15K":
        et.st2 = athlete
    elif distance == "30K":
        et.st3 = athlete
    elif distance == "10M":
        et.st4 = athlete
    elif distance == "25.6K":
        et.st5 = athlete
    elif distance == "10K":
        et.st6 = athlete
    elif distance == "Marathon":
        et.st7 = athlete
    et.save()


def get_member(event, result, membership):
    member = None
    lower_athlete = result["athlete"].lower()
    if lower_athlete in membership.names:
        member = membership.names[lower_athlete]
    if "{}-{}".format(event.id, result["place"]) in membership.includes:
        member = membership.includes["{}-{}".format(event.id, result["place"])]
    if member:
        if "{}-{}".format(event.id, result["place"]) in membership.excludes:
            if member in membership.excludes["{}-{}".format(event.id, result["place"])]:
                member = None
    return member


def process_rwpbs(event):
    pb_exclude_events = []
    rwpbs = {}
    members = (
        Result.objects.values("rwmember_id")
        .filter(event=event, rwmember__isnull=False)
        .values_list("rwmember_id", flat=True)
    )
    previous_results = Result.objects.filter(
        event__date__lt=event.date,
        event__distance=event.distance,
        rwmember_id__in=members,
    ).order_by("event__date")
    for i in previous_results:
        if i.rwmember_id in rwpbs:
            if i.guntime < rwpbs[i.rwmember_id]:
                rwpbs[i.rwmember_id] = i.guntime
        else:
            rwpbs[i.rwmember_id] = i.guntime
    future_results = Result.objects.filter(
        event__date__gte=event.date,
        event__distance=event.distance,
        rwmember_id__in=members,
    ).order_by("event__date")
    for i in future_results:
        i.isrwpb = False
        if (
            i.event.distance.slug != "roughly-five"
            and i.event.id not in pb_exclude_events
        ):
            if i.rwmember_id in rwpbs:
                if i.guntime < rwpbs[i.rwmember_id]:
                    rwpbs[i.rwmember_id] = i.guntime
                    i.isrwpb = True
            else:
                rwpbs[i.rwmember_id] = i.guntime
                i.isrwpb = True
        i.save()


def get_results_from_google(url):
    """Grab results from a Google Sheet"""
    gc = gspread.service_account("/root/google_service_account.json")
    sh = gc.open_by_url(url)
    results = {
        "individual": {},
        "team": {},
    }
    worksheet = sh.worksheet("individual")
    results["individual"] = worksheet.get_all_records()
    worksheet_list = [x.title for x in sh.worksheets()]
    if "team" in worksheet_list:
        worksheet = sh.worksheet("team")
        results["team"] = worksheet.get_all_records()
    return results


def get_extra_dict(result):
    extra_dict = {}
    for k, v in result.items():
        if k == "division":
            extra_dict["division"] = v
        elif k == "relay_team":
            extra_dict["relay_team"] = v
        elif k == "Hill Time":
            extra_dict["Hill Time"] = v
        elif "split" in k:
            extra_dict[k] = v
    return extra_dict
