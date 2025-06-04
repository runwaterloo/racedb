from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination

from ...models import Result
from .serializers import V1ResultSerializer


class V1ResultsPagination(PageNumberPagination):
    page_size = 50


class V1ResultsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = V1ResultSerializer
    pagination_class = V1ResultsPagination

    def get_queryset(self):
        queryset = Result.objects.all()
        event_id = self.request.query_params.get("event")
        if event_id is not None:
            queryset = queryset.filter(event_id=event_id).order_by("place")
        return queryset
