from datetime import date

from django.db.models import Min
from django.http.request import HttpRequest
from django.shortcuts import render
from django.template.defaulttags import register

from .models import Result, Rwmember, Rwmembertag


def index(request: HttpRequest):
    members, memberEventDates = order_members(
        Rwmember.objects.filter(active=True), request.GET.get("ordering", "id")
    )
    try:
        no_camera_tag = Rwmembertag.objects.get(name="no-profile-camera")
    except Exception:
        no_camera_members = []
    else:
        no_camera_members = Rwmember.objects.filter(tags=no_camera_tag)
    context = {
        "members": members,
        "no_camera_members": no_camera_members,
        "member_event_dates": memberEventDates,
    }
    return render(request, "racedbapp/members.html", context)


def order_members(members, ordering):
    results = (
        Result.objects.values("rwmember")
        .exclude(rwmember__isnull=True)
        .annotate(oldest_date=Min("event__date"))
    )
    memberEventDates = {}
    for result in results:
        if (
            result["rwmember"] in memberEventDates
            and memberEventDates[result["rwmember"]] < result["oldest_date"]
        ):
            continue
        memberEventDates[result["rwmember"]] = result["oldest_date"]
    if ordering == "date":
        members = sorted(members, key=lambda member: memberEventDates.get(member.id, date.today()))
    return members, memberEventDates


@register.filter
def get_date(dictionary, key):
    date = dictionary.get(key, "")
    if date != "":
        date = date.strftime("%Y")
    return date


@register.filter
def get_ranking(list, item):
    return list.index(item) + 1
