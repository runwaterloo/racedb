from rest_framework import viewsets

from ...models import Category, Distance, Race, Result
from .serializers import (
    V1CategorySerializer,
    V1DistanceSerializer,
    V1RaceSerializer,
    V1ResultSerializer,
)


class V1CategoriesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.all().order_by("id")
        return queryset


class V1DistancesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1DistanceSerializer

    def get_queryset(self):
        queryset = Distance.objects.all().order_by("id")
        return queryset


class V1RacesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1RaceSerializer

    def get_queryset(self):
        queryset = Race.objects.all().order_by("id")
        return queryset


class V1ResultsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1ResultSerializer

    def get_queryset(self):
        queryset = Result.objects.all()
        distance_id = self.kwargs.get("distance_pk") or self.kwargs.get("distance_id")
        if distance_id is not None:
            queryset = queryset.filter(event__distance_id=distance_id)
        event_id = self.request.query_params.get("event")  # TODO: remove this
        if event_id is not None:  # TODO: remove this
            queryset = queryset.filter(event_id=event_id)  # TODO: remove this
        return queryset.order_by("place")
