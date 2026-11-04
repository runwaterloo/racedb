from racedbapp.models import Config, Endurathlete, Result
from racedbapp.shared.tracing import tracer


def get_member_endurrace(result, membership):
    member = False
    lower_athlete = result.athlete.lower()
    if lower_athlete in membership.names:
        member = membership.names[lower_athlete]
    return member


def get_ultimate_finished_all_events(years):
    """
    Get a dictionary for Ultimates in each year and return True or False
    based on whether hey have completed (as an Ultimate) the most recent
    event from that year that has any results.
    """
    with tracer.start_as_current_span("records: ultimate finished-all-events"):
        return _get_ultimate_finished_all_events(years)


def _get_ultimate_finished_all_events(years):
    """Return {year: {Endurathlete: finished_last_event_of_year}}.

    Three bulk queries cover all years at once (the per-year approach
    was ~4 queries x N years of round-trip latency): last event per
    year, Ultimate finishers of those events, athletes for the years,
    and nothing else.
    """
    if not years:
        return {}
    min_year, max_year = min(years), max(years)
    # Last endurrun event with any results per year (one query over
    # results ordered newest-first; first hit per year wins).
    last_event_by_year = {}
    seen_years = set()
    result_rows = Result.objects.filter(
        event__race__slug="endurrun",
        event__date__year__gte=min_year,
        event__date__year__lte=max_year,
    ).order_by("-event__date").values_list("event__date__year", "event_id")
    for year, event_id in result_rows:
        if year not in seen_years:
            seen_years.add(year)
            last_event_by_year[year] = event_id
    # Ultimate finishers (place < 990000) of those last events.
    finishers = set(
        Result.objects.filter(
            event_id__in=last_event_by_year.values(), division="Ultimate", place__lt=990000
        ).values_list("event__date__year", "athlete")
    )
    # All Ultimate athletes for the years in play. Athletes in a year
    # with no endurrun results at all count as finished (the old
    # per-year code treated "no result_set" that way).
    athletes = Endurathlete.objects.filter(year__in=years)
    ultimate_finished_all_events = {}
    for year in years:
        ultimate_finished_all_events[year] = {}
    for athlete in athletes:
        finished = True
        if athlete.year in last_event_by_year:
            finished = (athlete.year, athlete.name) in finishers
        ultimate_finished_all_events[athlete.year][athlete] = finished
    return ultimate_finished_all_events


def get_endurrun_same_name_dict():
    """
    Return a dictionary of names that are the same as each other, based on
    endurrun_same_name objects in Config
    """
    same_name_dict = {}
    db_same_names = Config.objects.filter(name="endurrun_same_name").values_list("value", flat=True)
    for i in db_same_names:
        names = [x.strip() for x in i.split(";")]
        for name in names:
            same_name_dict[name] = names
    return same_name_dict


def get_ultimate_winners_and_gold_jerseys(years, athletes) -> tuple[set | None, set | None]:
    """
    Get a list of names of people who have won the ENDURrun ultimate.
    If there is ever a tie for winner times in a year, this won't work.
    """
    same_name_dict = get_endurrun_same_name_dict()
    ultimate_winners = []
    ultimate_gold_jerseys = []
    if not athletes:
        return None, None
    for year in years:
        year_results = Result.objects.filter(
            event__race__slug="endurrun",
            division="Ultimate",
            place__lt=990000,
            event__date__icontains=year,
        ).order_by("event__date")
        athlete_event_count = {}
        female_cumulative_time = {}
        male_cumulative_time = {}
        event_ids = year_results.values_list("event__id", flat=True).distinct()
        num_events = 0
        for event_id in event_ids:
            num_events += 1
            event_results = year_results.filter(event_id=event_id)
            for result in event_results:
                if result.athlete in athlete_event_count:
                    athlete_event_count[result.athlete] += 1
                else:
                    athlete_event_count[result.athlete] = 1
                if result.gender == "F":
                    if result.athlete in female_cumulative_time:
                        female_cumulative_time[result.athlete] += result.guntime
                    else:
                        female_cumulative_time[result.athlete] = result.guntime
                if result.gender == "M":
                    if result.athlete in male_cumulative_time:
                        male_cumulative_time[result.athlete] += result.guntime
                    else:
                        male_cumulative_time[result.athlete] = result.guntime
            if female_cumulative_time:
                female_cumulative_time = {
                    key: val
                    for key, val in female_cumulative_time.items()
                    if athlete_event_count[key] == num_events
                }
                female_gold_jersey = min(female_cumulative_time, key=female_cumulative_time.get)
                ultimate_gold_jerseys.append(female_gold_jersey)
                if num_events == 7:
                    ultimate_winners.append(female_gold_jersey)
            if male_cumulative_time:
                male_cumulative_time = {
                    key: val
                    for key, val in male_cumulative_time.items()
                    if athlete_event_count[key] == num_events
                }
                male_gold_jersey = min(male_cumulative_time, key=male_cumulative_time.get)
                ultimate_gold_jerseys.append(male_gold_jersey)
                if num_events == 7:
                    ultimate_winners.append(male_gold_jersey)
    for athlete in athletes:
        if athlete in same_name_dict:
            for same_name in same_name_dict[athlete]:
                if same_name in ultimate_winners:
                    ultimate_winners.append(athlete)
                if same_name in ultimate_gold_jerseys:
                    ultimate_gold_jerseys.append(athlete)
    ultimate_winners = set(ultimate_winners)
    ultimate_gold_jerseys = set(ultimate_gold_jerseys)
    return ultimate_winners, ultimate_gold_jerseys


def get_ultimate_gp():
    """
    Calculate the gender place of all ultimates regardless of filters, etc
    """
    ultimate_gp = {}
    ultimate_gp1 = {}
    ultimate_gp_female = {}
    ultimate_gp_male = {}
    ultimate_gp_starters = {}
    ultimate_results = Result.objects.filter(
        event__race__slug="endurrun",
        division="Ultimate",
        place__lt=990000,
    ).select_related("event")
    years = ultimate_results.values("event__date__year").distinct().order_by()
    for year in years:
        ultimate_gp[year.get("event__date__year")] = {}
        ultimate_gp1[year.get("event__date__year")] = {}
        ultimate_gp_female[year.get("event__date__year")] = {}
        ultimate_gp_male[year.get("event__date__year")] = {}
    for result in ultimate_results:
        if result.athlete in ultimate_gp1[result.event.date.year]:
            ultimate_gp1[result.event.date.year][result.athlete]["events"] += 1
            ultimate_gp1[result.event.date.year][result.athlete]["total_time"] += result.guntime
        else:
            ultimate_gp1[result.event.date.year][result.athlete] = {
                "events": 1,
                "gender": result.gender,
                "total_time": result.guntime,
            }
    for year, athlete in ultimate_gp1.items():  # copy over only results with 7 events
        ultimate_gp_starters[year] = {"F": 0, "M": 0}
        for name, data in athlete.items():
            ultimate_gp_starters[year][data["gender"]] += 1
            if data["events"] == 7:
                if data["gender"] == "F":
                    ultimate_gp_female[year][name] = data["total_time"]
                elif data["gender"] == "M":
                    ultimate_gp_male[year][name] = data["total_time"]
    for year in ultimate_gp_female.keys():
        female_rank = {
            key: rank
            for rank, key in enumerate(
                sorted(ultimate_gp_female[year], key=ultimate_gp_female[year].get), 1
            )
        }
        for k, v in female_rank.items():
            female_rank[k] = "{}/{}".format(v, ultimate_gp_starters[year]["F"])
        male_rank = {
            key: rank
            for rank, key in enumerate(
                sorted(ultimate_gp_male[year], key=ultimate_gp_male[year].get), 1
            )
        }
        for k, v in male_rank.items():
            male_rank[k] = "{}/{}".format(v, ultimate_gp_starters[year]["M"])
        ultimate_gp[year] = female_rank | male_rank
    return ultimate_gp
