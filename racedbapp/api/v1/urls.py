from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import V1ResultsViewSet

router = DefaultRouter()
router.register(r"results", V1ResultsViewSet, basename="v1-results")

urlpatterns = [
    path("", include(router.urls)),
]
