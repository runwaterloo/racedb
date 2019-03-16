from django.http import Http404, HttpResponse
import urllib
from datetime import datetime
from .models import Config
from .tasks import photoupdate
import logging

logger = logging.getLogger(__name__)


def index(request):
    qstring = urllib.parse.parse_qs(request.META["QUERY_STRING"])
    notifykey = Config.objects.filter(name="notifykey")[0].value
    if "notifykey" not in qstring:
        logger.warning("missing key")
        raise Http404('Parameter "notifykey" not in URL')
    elif qstring["notifykey"][0] != notifykey:
        logger.warning("invalid key")
        raise Http404("Invalid key")
    elif "date" not in qstring:
        logger.warning("missing date")
        raise Http404('Parameter "date" not in URL')
    else:
        request_date = qstring["date"][0]
    if request_date not in ("auto", "all"):
        try:
            datetime.strptime(request_date, "%Y-%m-%d")
        except ValueError:
            logger.warning("invalid date format")
            raise Http404("Invalid date format, should be YYYY-MM-DD")
    photoupdate.delay(request_date=request_date)
    return HttpResponse("Photo update request received")
