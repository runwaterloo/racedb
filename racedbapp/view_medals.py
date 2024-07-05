from django.http import Http404
from django.shortcuts import render

# from urllib import parse
# from collections import defaultdict, namedtuple
from .models import Event, Result
from .shared import utils

# from racedbapp.tasks import send_email_task
# from . import view_shared, utils
# from django.http import HttpResponse
# from django.db.models import Count, Max, Q
# from datetime import timedelta
# from operator import attrgetter
# import simplejson


def index(request, year, race_slug, distance_slug):
    try:
        event = Event.objects.select_related().get(
            race__slug=race_slug, distance__slug=distance_slug, date__icontains=year
        )
    except Exception:
        raise Http404("Matching event not found")
    else:
        event_results = Result.objects.filter(event=event)
    guntimes_have_microseconds = set(
        [x.guntime.microseconds for x in event_results if x.guntime.microseconds != 0]
    )
    medals_type = event.medals
    medal_results = get_medal_results(medals_type, event_results)
    race_logo_slug = utils.get_race_logo_slug(event.race.slug)

    context = {
        "event": event,
        "race_logo_slug": race_logo_slug,
        "guntimes_have_microseconds": guntimes_have_microseconds,
        "medal_results": medal_results,
    }
    return render(request, "racedbapp/medals.html", context)


def get_medal_results(medals_type, event_results):
    medal_results = []
    award_counts = {
        "F": 0,
        "M": 0,
        "FM": 0,
        "MM": 0,
    }
    for er in event_results:
        mr = MedalResult(er)
        medal_results.append(mr)
        mr.award = ""
        if er.category.name == "":
            continue
        if medals_type == "standard":
            if er.gender == "F":
                if award_counts["F"] == 0:
                    mr.award = "1st Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 1:
                    mr.award = "2nd Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 2:
                    mr.award = "3rd Overall Female"
                    award_counts["F"] += 1
                if mr.award == "" and er.category.ismasters:
                    if award_counts["FM"] == 0:
                        mr.award = "1st Masters Female"
                        award_counts["FM"] += 1
                    elif award_counts["FM"] == 1:
                        mr.award = "2nd Masters Female"
                        award_counts["FM"] += 1
                    elif award_counts["FM"] == 2:
                        mr.award = "3rd Masters Female"
                        award_counts["FM"] += 1
            if er.gender == "M":
                if award_counts["M"] == 0:
                    mr.award = "1st Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 1:
                    mr.award = "2nd Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 2:
                    mr.award = "3rd Overall Male"
                    award_counts["M"] += 1
                if mr.award == "" and er.category.ismasters:
                    if award_counts["MM"] == 0:
                        mr.award = "1st Masters Male"
                        award_counts["MM"] += 1
                    elif award_counts["MM"] == 1:
                        mr.award = "2nd Masters Male"
                        award_counts["MM"] += 1
                    elif award_counts["MM"] == 2:
                        mr.award = "3rd Masters Male"
                        award_counts["MM"] += 1
            if mr.award == "":
                if er.category.name not in award_counts:
                    mr.award = "1st {}".format(er.category.name)
                    award_counts[er.category.name] = 1
                elif award_counts[er.category.name] == 1:
                    mr.award = "2nd {}".format(er.category.name)
                    award_counts[er.category.name] += 1
                elif award_counts[er.category.name] == 2:
                    mr.award = "3rd {}".format(er.category.name)
                    award_counts[er.category.name] += 1
        elif medals_type == "classic-5oa":
            if er.gender == "F":
                if award_counts["F"] == 0:
                    mr.award = "1st Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 1:
                    mr.award = "2nd Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 2:
                    mr.award = "3rd Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 3:
                    mr.award = "4th Overall Female"
                    award_counts["F"] += 1
                elif award_counts["F"] == 4:
                    mr.award = "5th Overall Female"
                    award_counts["F"] += 1
                if mr.award == "" and er.category.ismasters:
                    if award_counts["FM"] == 0:
                        mr.award = "1st Masters Female"
                        award_counts["FM"] += 1
                    elif award_counts["FM"] == 1:
                        mr.award = "2nd Masters Female"
                        award_counts["FM"] += 1
                    elif award_counts["FM"] == 2:
                        mr.award = "3rd Masters Female"
                        award_counts["FM"] += 1
            if er.gender == "M":
                if award_counts["M"] == 0:
                    mr.award = "1st Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 1:
                    mr.award = "2nd Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 2:
                    mr.award = "3rd Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 3:
                    mr.award = "4th Overall Male"
                    award_counts["M"] += 1
                elif award_counts["M"] == 4:
                    mr.award = "5th Overall Male"
                    award_counts["M"] += 1
                if mr.award == "" and er.category.ismasters:
                    if award_counts["MM"] == 0:
                        mr.award = "1st Masters Male"
                        award_counts["MM"] += 1
                    elif award_counts["MM"] == 1:
                        mr.award = "2nd Masters Male"
                        award_counts["MM"] += 1
                    elif award_counts["MM"] == 2:
                        mr.award = "3rd Masters Male"
                        award_counts["MM"] += 1
                    elif award_counts["MM"] == 2:
                        mr.award = "3rd Masters Male"
                        award_counts["MM"] += 1
            if mr.award == "":
                if er.category.name not in award_counts:
                    mr.award = "1st {}".format(er.category.name)
                    award_counts[er.category.name] = 1
                elif award_counts[er.category.name] == 1:
                    mr.award = "2nd {}".format(er.category.name)
                    award_counts[er.category.name] += 1
                elif award_counts[er.category.name] == 2:
                    mr.award = "3rd {}".format(er.category.name)
                    award_counts[er.category.name] += 1
        else:
            mr.award = "none"
    return medal_results


class MedalResult:
    def __init__(self, result):
        self.bib = result.bib
        self.athlete = result.athlete
        self.guntime = result.guntime
        self.member_slug = False
        if result.rwmember:
            if result.rwmember.active:
                self.member_slug = result.rwmember.slug
