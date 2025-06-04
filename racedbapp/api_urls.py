from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView


class V1Root(APIView):
    def get(self, request):
        return Response({"message": "Welcome to the API v1 root."})


urlpatterns = [
    path("", V1Root.as_view(), name="v1-root"),
]
