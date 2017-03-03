from django.http import JsonResponse
import urllib
from .models import *

def index(request):
    qstring = urllib.parse.parse_qs(request.META['QUERY_STRING'])
    notifykey = Config.objects.filter(name='notifykey')[0].value
    if 'notifykey' not in qstring:
        response = {'result': 'fail',
                    'message': 'missing key'}
    elif qstring['notifykey'][0] != notifykey:
        response = {'result': 'fail',
                    'message': 'invalid key'}
    elif 'date' not in qstring:
        response = {'result': 'fail',
                    'message': 'missing date'}
    else:
        response = {'result': 'Success',
                    'message': 'Thank you, come again.'}
    return JsonResponse(response)
