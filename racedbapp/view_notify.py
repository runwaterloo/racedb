import urllib
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import render

from .exceptions import ResultImportError
from .models import Config


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    notifykey = Config.objects.filter(name="notifykey")[0].value
    if "notifykey" in qstring:
        if qstring["notifykey"][0] == notifykey:
            output = StringIO()
            if "event_id" in qstring:
                event_id = qstring["event_id"][0]
            else:
                event_id = None
            try:
                if event_id is not None:
                    call_command("addraces", event_id=event_id, stdout=output)
                else:
                    call_command("addraces", stdout=output)
            except ResultImportError as exc:
                if getattr(exc, "partial", False):
                    context = {
                        "header": "Import Partial Success",
                        "badge_class": "yellow",
                        "status": 422,
                        "output": str(exc),
                    }
                else:
                    context = {
                        "header": "Import Failed",
                        "badge_class": "red",
                        "status": 422,
                        "output": str(exc),
                    }
                return render(request, "racedbapp/notify_result.html", context, status=422)
            context = {
                "header": "Import Success",
                "badge_class": "green",
                "status": 200,
                "output": output.getvalue(),
            }
            return render(request, "racedbapp/notify_result.html", context)
        else:
            return HttpResponse("Correct notification key not sent")
    else:
        return HttpResponse("Correct notification key not sent")
