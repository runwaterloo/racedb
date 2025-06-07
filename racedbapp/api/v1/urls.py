from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import V1CategoriesViewSet, V1DistancesViewSet, V1RacesViewSet, V1ResultsViewSet

router = DefaultRouter()
router.register(r"categories", V1CategoriesViewSet, basename="v1-categories")
router.register(r"distances", V1DistancesViewSet, basename="v1-distances")
router.register(r"races", V1RacesViewSet, basename="v1-races")
router.register(r"results", V1ResultsViewSet, basename="v1-results")

# Nested router for /distances/<distance_id>/results
results_nested_router = NestedDefaultRouter(router, r"distances", lookup="distance")
results_nested_router.register(r"results", V1ResultsViewSet, basename="v1-distance-results")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(results_nested_router.urls)),
]
