import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from racedbapp import tasks

from .models import Config

logger = logging.getLogger(__name__)


@csrf_exempt
def index(request):
    if "HTTP_X_GITLAB_TOKEN" in request.META:
        gitlabtoken = request.META["HTTP_X_GITLAB_TOKEN"]
    else:
        gitlabtoken = None
    notifykey = Config.objects.get(name="notifykey").value
    if gitlabtoken == notifykey:
        response = "Hook received"
        logger.info(response)
        tasks.webhook.delay()
    else:
        response = "Invalid hook (bad or missing token)"
        logger.warning(response)
    return HttpResponse(response)
