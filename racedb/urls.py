"""racedb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

import os

from django.contrib import admin
from django.urls import include, path, re_path

urlpatterns = [
    path("", include("django_prometheus.urls")),
    re_path(r"^admin/", admin.site.urls),
    path("v1/", include("racedbapp.api.v1.urls")),
    path("", include("racedbapp.urls")),
]

if os.environ.get("ENABLE_DEBUG_TOOLBAR", "false") == "true":
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
