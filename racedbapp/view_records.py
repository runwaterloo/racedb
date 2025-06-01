import urllib
from collections import namedtuple

import simplejson
from django.http import HttpResponse
from django.shortcuts import render

from .models import Distance, Race
from .shared import shared


def index(request, race_slug, distance_slug):
    """
    Main view for displaying race records.
    Determines the race and distance, builds the context, and returns either
    an HTML page or JSON/JSONP response depending on the query string.
    """
    # Parse query string parameters from the request
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])

    # Resolve the race and distance objects from slugs
    race = resolve_race(race_slug)
    distance = resolve_distance(distance_slug)

    # Build the context dictionary for the template or JSON
    context = build_context(race, distance)

    # Return JSON/JSONP if requested, otherwise render the HTML template
    if "format" in qstring:
        if qstring["format"][0] == "json":
            # Support JSONP if 'callback' is present
            callback = qstring.get("callback", [None])[0]
            data, content_type = render_json_context(context, callback)
            return HttpResponse(data, content_type)
        else:
            return HttpResponse("Unknown format in URL", "text/html")
    else:
        return render(request, "racedbapp/records.html", context)


def resolve_race(race_slug):
    """
    Look up a Race by slug and return a namedtuple with its key fields.
    """
    rawrace = Race.objects.get(slug=race_slug)
    namedrace = namedtuple("nr", ["id", "name", "shortname", "slug"])
    return namedrace(rawrace.id, rawrace.name, rawrace.shortname, rawrace.slug)


def resolve_distance(distance_slug):
    """
    Look up a Distance by slug and return a namedtuple with its key fields.
    Special case: if slug is 'combined', return a hardcoded Combined distance.
    """
    nameddistance = namedtuple("nd", ["id", "name", "slug", "km"])
    if distance_slug == "combined":
        # Combined is a special pseudo-distance
        return nameddistance(0, "Combined", distance_slug, 13)
    else:
        rawdistance = Distance.objects.get(slug=distance_slug)
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


def render_json_context(context, callback=None):
    """
    Serialize the context dictionary to JSON or JSONP if a callback is provided.
    Returns a tuple of (data, content_type).
    """
    data = simplejson.dumps(context, default=str, indent=4, sort_keys=True)
    if callback:
        # JSONP support: wrap in callback function
        return "{}({});".format(callback, data), "text/javascript"
    else:
        return data, "application/json"
