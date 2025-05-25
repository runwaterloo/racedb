from collections import namedtuple
from datetime import timedelta
from operator import attrgetter

from django.shortcuts import render

from .models import Bow, Bowathlete, Category, Event, Result


def index(request, bow_slug, phase):
    bow = Bow.objects.get(slug=bow_slug)
    event_ids = eval(Bow.objects.get(slug=bow_slug).events)
    events = Event.objects.filter(id__in=(event_ids)).order_by("date")[0 : int(phase)]
    athletes = Bowathlete.objects.filter(bow=bow)
    if int(phase) == len(event_ids):
        heading = "Final Results"
    elif int(phase) == 1:
        heading = "Results After {} Event".format(phase)
    else:
        heading = "Results After {} Events".format(phase)
    category_ids = Bowathlete.objects.filter(bow=bow).values_list("category", flat=True).distinct()
    categories = Category.objects.filter(id__in=(category_ids)).order_by("name")
    all_event_results = []
    for event in events:
        event_results = Result.objects.filter(event=event)
        event_dict = dict(event_results.values_list("athlete", "guntime"))
        all_event_results.append(event_dict)
    full_results = []
    namedfullresult = namedtuple(
        "na",
        ["athlete", "category", "stages", "total_time", "total_seconds", "stage_times"],
    )
    for athlete in athletes:
        category = athlete.category
        stages = 0
        stage_times = []
        total_time = timedelta(seconds=0)
        for er in all_event_results:
            try:
                stage_time = er[athlete.name]
            except Exception:
                stage_time = timedelta(seconds=0)
            else:
                stages += 1
            total_time += stage_time
            stage_times.append(stage_time)
        if total_time == timedelta(seconds=0):
            total_seconds = 0
            total_time = ""
        else:
            total_seconds = total_time.total_seconds()
        if stages == int(phase):
            full_results.append(
                namedfullresult(athlete, category, stages, total_time, total_seconds, stage_times)
            )
    full_results = sorted(full_results, key=attrgetter("total_seconds"))
    full_results = sorted(full_results, key=attrgetter("stages"), reverse=True)
    recap_categories = []
    for category in categories:
        if category.name[1:] not in recap_categories:
            recap_categories.append(category.name[1:])
    result_leader_dict = {}
    for r in full_results:
        if r.category not in result_leader_dict:
            result_leader_dict[r.category] = r
    namedresult = namedtuple(
        "nr", ["category", "female_athlete", "female_time", "male_athlete", "male_time"]
    )
    results = []
    female_results = [x for x in full_results if x.category.name[0] == "F"]
    female_leader = female_results[0]
    master_female_results = [x for x in female_results if x.category.ismasters]
    masters_female_leader = master_female_results[0]
    male_results = [x for x in full_results if x.category.name[0] == "M"]
    male_leader = male_results[0]
    master_male_results = [x for x in male_results if x.category.ismasters]
    masters_male_leader = master_male_results[0]
    results.append(
        namedresult(
            "Overall",
            female_leader.athlete.name,
            female_leader.total_time,
            male_leader.athlete.name,
            male_leader.total_time,
        )
    )
    results.append(
        namedresult(
            "Masters",
            masters_female_leader.athlete.name,
            masters_female_leader.total_time,
            masters_male_leader.athlete.name,
            masters_male_leader.total_time,
        )
    )
    for category in sorted(recap_categories):
        female_cat_results = [x for x in female_results if category in x.athlete.category.name]
        if len(female_cat_results) == 0:
            female_leader = ""
            female_time = ""
        else:
            female_leader = female_cat_results[0].athlete.name
            female_time = female_cat_results[0].total_time
        male_cat_results = [x for x in male_results if category in x.athlete.category.name]
        if len(male_cat_results) == 0:
            male_leader = ""
            male_time = ""
        else:
            male_leader = male_cat_results[0].athlete.name
            male_time = male_cat_results[0].total_time
        if male_leader == "" and female_leader == "":
            continue
        results.append(namedresult(category, female_leader, female_time, male_leader, male_time))
    context = {"bow": bow, "heading": heading, "results": results, "nomenu": True}
    return render(request, "racedbapp/bowrecap.html", context)
