from django.http import JsonResponse
from .models import Result
import os

def index(request):
    build = os.environ.get('BUILD', 'unknown-build')
    numresults = Result.objects.count()
    response = {
        "build": build,
        "numresults": numresults,
    }
    return JsonResponse(response)
