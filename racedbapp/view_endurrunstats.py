from operator import attrgetter

from django.db.models import Count
from django.shortcuts import render

from . import view_shared
from .models import Result


def index(request):
    ultimate_results = get_ultimate_results()
    years = get_years(ultimate_results)
    min_finishes = get_min_finishes()
    endurrun_finishers_by_year = get_endurrun_finishers_by_year(ultimate_results, years)
    endurrun_finishes_by_athlete = get_endurrun_finishes_by_athlete(
        endurrun_finishers_by_year
    )
    member_dict = view_shared.get_member_dict()
    endurrun_finishers_by_count = get_endurrun_finishers_by_count(
        endurrun_finishes_by_athlete, member_dict, years, min_finishes
    )
    context = {
        "results": endurrun_finishers_by_count,
        "min_finishes": min_finishes,
    }
    return render(request, "racedbapp/endurrunstats.html", context)


def get_min_finishes():
    min_finishes = view_shared.get_config_value_or_false("endurrun_stats_min_finishes")
    if min_finishes:
        min_finishes = int(min_finishes)
    return min_finishes


def get_ultimate_results():
    ultimate_results = Result.objects.filter(
        event__race__slug="endurrun",
        division="Ultimate",
        place__lt=990000,
    ).select_related("event")
    return ultimate_results


def get_years(ultimate_results):
    years = (
        ultimate_results.values_list("event__date__year", flat=True)
        .distinct()
        .order_by("-event__date__year")
    )
    return years


def get_endurrun_finishers_by_year(ultimate_results, years):
    endurrun_finishers_by_year = {}
    for year in years:
        year_results = ultimate_results.filter(event__date__year=year)
        athlete_finishes = (
            year_results.values("athlete")
            .annotate(finishes=Count("athlete"))
            .order_by()
            .filter(finishes=7)
        ).values_list("athlete", flat=True)
        endurrun_finishers_by_year[year] = athlete_finishes
    return endurrun_finishers_by_year


def get_endurrun_finishes_by_athlete(endurrun_finishers_by_year):
    endurrun_finishes_by_athlete = {}
    same_name_dict = view_shared.get_endurrun_same_name_dict()
    for year, finishers in endurrun_finishers_by_year.items():
        for athlete in finishers:
            if athlete in endurrun_finishes_by_athlete:
                endurrun_finishes_by_athlete[athlete] += 1
            elif athlete not in same_name_dict:
                endurrun_finishes_by_athlete[athlete] = 1
            else:
                found = False
                for name in same_name_dict[athlete]:
                    if name in endurrun_finishes_by_athlete:
                        endurrun_finishes_by_athlete[name] += 1
                        found = True
                if not found:
                    endurrun_finishes_by_athlete[athlete] = 1
    return endurrun_finishes_by_athlete


def get_endurrun_finishers_by_count(
    endurrun_finishes_by_athlete, member_dict, years, min_finishes
):

    raw_endurrun_finishers_by_count = {}
    endurrun_finishers_by_count = []
    for athlete, count in endurrun_finishes_by_athlete.items():
        if count < min_finishes:
            continue
        if count in raw_endurrun_finishers_by_count:
            raw_endurrun_finishers_by_count[count].append(athlete)
        else:
            raw_endurrun_finishers_by_count[count] = [athlete]
    all_athletes = []
    for count, athlete_list in raw_endurrun_finishers_by_count.items():
        all_athletes += athlete_list
        finish_count = EndurrunFinishCount(count, athlete_list, member_dict)
        endurrun_finishers_by_count.append(finish_count)
    endurrun_finishers_by_count = sorted(
        endurrun_finishers_by_count, key=attrgetter("count"), reverse=True
    )
    (
        ultimate_winners,
        ultimate_gold_jerseys,
    ) = view_shared.get_ultimate_winners_and_gold_jerseys(years, set(all_athletes))
    for count in endurrun_finishers_by_count:
        for athlete in count.athletes:
            if athlete.athlete in ultimate_winners:
                athlete.winner = True
            elif athlete.athlete in ultimate_gold_jerseys:
                athlete.gold_jersey = True
    return endurrun_finishers_by_count


class EndurrunFinisher:
    def __init__(self, athlete, member_dict):
        self.athlete = athlete
        self.last_name = self.athlete.split()[-1]
        member = member_dict.get(self.athlete.lower(), False)
        if member:
            self.member_slug = member.slug
        else:
            self.member_slug = False
        self.winner = False
        self.gold_jersey = False

    def __repr__(self):
        return "EndurrunFinisher(athlete={}, member_slug={})".format(
            self.athlete, self.member_slug
        )


class EndurrunFinishCount:
    def __init__(self, count, athlete_list, member_dict):
        self.count = count
        self.athletes = sorted(
            (EndurrunFinisher(x, member_dict) for x in athlete_list),
            key=attrgetter("last_name"),
        )

    def __repr__(self):
        return "EndurrunFinishCount(count={}, athletes={})".format(
            self.count, self.athletes
        )
