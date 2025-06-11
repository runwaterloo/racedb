from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (
    V1CategoriesViewSet,
    V1DistancesViewSet,
    V1EventsViewSet,
    V1RacesViewSet,
    V1ResultsViewSet,
    V1RwmembersViewSet,
    V1SeriesViewSet,
)

router = DefaultRouter()
router.register(r"categories", V1CategoriesViewSet, basename="v1-categories")
router.register(r"distances", V1DistancesViewSet, basename="v1-distances")
router.register(r"events", V1EventsViewSet, basename="v1-events")
router.register(r"rwmembers", V1RwmembersViewSet, basename="v1-rwmembers")
router.register(r"races", V1RacesViewSet, basename="v1-races")
router.register(r"results", V1ResultsViewSet, basename="v1-results")
router.register(r"series", V1SeriesViewSet, basename="v1-series")

# Nested router for /distances/<distance_id>/results
distance_results_router = NestedDefaultRouter(router, r"distances", lookup="distance")
distance_results_router.register(r"results", V1ResultsViewSet, basename="v1-distance-results")

# Nested router for /events/<event_id>/results
event_results_router = NestedDefaultRouter(router, r"events", lookup="event")
event_results_router.register(r"results", V1ResultsViewSet, basename="v1-event-results")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(distance_results_router.urls)),
    path("", include(event_results_router.urls)),
]
