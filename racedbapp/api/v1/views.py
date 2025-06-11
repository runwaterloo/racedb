from django.db.models import Exists, OuterRef
from rest_framework import viewsets

from ...models import Category, Distance, Event, Race, Result, Rwmember, Series
from .serializers import (
    V1CategorySerializer,
    V1DistanceSerializer,
    V1EventSerializer,
    V1RaceSerializer,
    V1ResultSerializer,
    V1RwmemberSerializer,
    V1SeriesSerializer,
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


class V1EventsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1EventSerializer

    def get_queryset(self):
        queryset = Event.objects.select_related("race", "distance")
        queryset = queryset.annotate(
            results_exist=Exists(Result.objects.filter(event=OuterRef("pk")))
        )

        # filter by year
        year = self.request.query_params.get("year")
        if year:
            queryset = queryset.filter(date__year=year)

        # filter by distance
        distance_slug = self.request.query_params.get("distance_slug")
        if distance_slug:
            queryset = queryset.filter(distance__slug=distance_slug)

        # filter by race
        race_slug = self.request.query_params.get("race_slug")
        if race_slug:
            queryset = queryset.filter(race__slug=race_slug)

        # filter by results_exist
        results_exist = self.request.query_params.get("results_exist")
        if results_exist is not None:
            if results_exist.lower() == "true":
                queryset = queryset.filter(results_exist=True)
            elif results_exist.lower() == "false":
                queryset = queryset.filter(results_exist=False)

        return queryset.order_by("-date")


class V1RwmembersViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1RwmemberSerializer

    def get_queryset(self):
        queryset = Rwmember.objects.filter(active=True).order_by("id")
        return queryset


class V1RacesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1RaceSerializer

    def get_queryset(self):
        queryset = Race.objects.all().order_by("id")
        return queryset


class V1ResultsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1ResultSerializer

    def get_queryset(self):
        queryset = Result.objects.select_related("rwmember", "category")
        distance_id = self.kwargs.get("distance_pk") or self.kwargs.get("distance_id")
        if distance_id is not None:
            queryset = queryset.filter(event__distance_id=distance_id)
        event_id = self.kwargs.get("event_pk") or self.kwargs.get("event_id")
        if event_id is not None:
            queryset = queryset.filter(event_id=event_id)
        return queryset.order_by("place")


class V1SeriesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1SeriesSerializer

    def get_queryset(self):
        queryset = Series.objects.all().order_by("id")
        return queryset
