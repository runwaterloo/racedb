from django.http import JsonResponse
from django.core.management import call_command
import urllib
from .models import *

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    notifykey = Config.objects.filter(name='notifykey')[0].value
    response = {'result': 'fail',
                'message': 'correct notification key not sent'}
    if 'notifykey' in qstring:
        if qstring['notifykey'][0] == notifykey:
            call_command('addraces')
            response = {'result': 'Success',
                        'message': 'Thank you, come again.'}
    return JsonResponse(response)
