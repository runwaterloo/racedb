from django.http import JsonResponse
from .models import Race


def index(request):
    race_slugs = list(Race.objects.values_list("slug", flat=True))
    response = {
        "race_slugs": race_slugs,
    }
    return JsonResponse(response)