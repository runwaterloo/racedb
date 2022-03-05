import urllib

from django.http import JsonResponse

from racedbapp import tasks

from .models import Config


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    notifykey = Config.objects.filter(name="notifykey")[0].value
    response = {"result": "fail", "message": "correct notification key not sent"}
    if "notifykey" in qstring:
        if qstring["notifykey"][0] == notifykey:
            tasks.clear_cache.delay()
            response = {"result": "Success", "message": "Cache cleared"}
    return JsonResponse(response)
