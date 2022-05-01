import urllib
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse

from .models import Config


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    notifykey = Config.objects.filter(name="notifykey")[0].value
    if "notifykey" in qstring:
        if qstring["notifykey"][0] == notifykey:
            output = StringIO()
            if "event_id" in qstring:
                event_id = qstring["event_id"][0]
                call_command("addraces", event_id=event_id, stdout=output)
            else:
                call_command("addraces", stdout=output)
            return HttpResponse(output.getvalue(), content_type="text/plain")
        else:
            return HttpResponse("Correct notification key not sent")
    else:
        return HttpResponse("Correct notification key not sent")
