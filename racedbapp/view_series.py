from urllib import parse

from django.shortcuts import render

from .models import Series


def index(request, series_slug):
    qstring = parse.parse_qs(request.META["QUERY_STRING"])
    year = False
    series = Series.objects.filter(slug=series_slug)
    if "year" in qstring:
        year = int(qstring["year"][0])
        series = series.filter(year=year)
    context = {
        "series": series,
        "year": year,
    }
    return render(request, "racedbapp/series.html", context)
