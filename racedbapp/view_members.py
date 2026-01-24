from django.db.models import Min
from django.http.request import HttpRequest
from django.shortcuts import render

from .models import Rwmember, Rwmembertag


def index(request: HttpRequest):
    members = get_members_with_first_result(request.GET.get("ordering", "id"))
    try:
        no_camera_tag = Rwmembertag.objects.get(name="no-profile-camera")
    except Exception:
        no_camera_members = []
    else:
        no_camera_members = Rwmember.objects.filter(tags=no_camera_tag)
    context = {
        "members": members,
        "no_camera_members": no_camera_members,
    }
    return render(request, "racedbapp/members.html", context)


def get_members_with_first_result(ordering):
    """
    Get active members annotated with their oldest event date.
    All sorting is done at the database level for performance.
    """
    # Annotate each member with the minimum event date from their results
    members = Rwmember.objects.filter(active=True).annotate(
        first_result_date=Min("result__event__date")
    )

    if ordering == "date":
        # Sort by first result date, with nulls (no results) at the end
        members = members.order_by("first_result_date")
    else:
        members = members.order_by("id")

    return members
