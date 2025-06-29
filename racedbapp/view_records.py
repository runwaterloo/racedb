from collections import namedtuple

from django.http import Http404
from django.shortcuts import render

from .models import Distance, Race
from .shared import shared


def index(request, race_slug, distance_slug):
    """
    Main view for displaying race records.
    Determines the race and distance, builds the context, and returns either
    an HTML page or JSON/JSONP response depending on the query string.
    """

    # Resolve the race and distance objects from slugs
    race = resolve_race(race_slug)
    distance = resolve_distance(distance_slug)
    x
    # Build the context dictionary for the template or JSON
    context = build_context(race, distance)

    # Return the response
    return render(request, "racedbapp/records.html", context)


def resolve_race(race_slug):
    """
    Look up a Race by slug and return a namedtuple with its key fields. Return 404
    if not found.
    """
    try:
        rawrace = Race.objects.get(slug=race_slug)
    except Race.DoesNotExist:
        raise Http404(f"Race with slug '{race_slug}' not found.")
    namedrace = namedtuple("nr", ["id", "name", "shortname", "slug"])
    return namedrace(rawrace.id, rawrace.name, rawrace.shortname, rawrace.slug)


def resolve_distance(distance_slug):
    """
    Look up a Distance by slug and return a namedtuple with its key fields. Return 404
    if not found. Special case: if slug is 'combined', return a hardcoded Combined distance.
    """
    nameddistance = namedtuple("nd", ["id", "name", "slug", "km"])
    if distance_slug == "combined":
        # Combined is a special pseudo-distance
        return nameddistance(0, "Combined", distance_slug, 13)
    else:
        try:
            rawdistance = Distance.objects.get(slug=distance_slug)
        except Distance.DoesNotExist:
            raise Http404(f"Distance with slug '{distance_slug}' not found.")
        return nameddistance(rawdistance.id, rawdistance.name, rawdistance.slug, rawdistance.km)


def build_context(race, distance):
    """
    Build the context dictionary for rendering or JSON output.
    Calls shared.get_race_records to get all relevant records for the race/distance.
    """
    records, team_records, hill_records = shared.get_race_records(race, distance)
    return {
        "race": race,
        "distance": distance,
        "records": records,
        "team_records": team_records,
        "hill_records": hill_records,
        "nomenu": True,  # Used by the template to hide the menu
    }
