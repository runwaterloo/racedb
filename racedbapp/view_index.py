from django.http import HttpResponse

def index(request):
    return HttpResponse('Nothing to see here.')
