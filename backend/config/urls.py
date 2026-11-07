from django.contrib import admin
from django.urls import include, path

from routing.views import ApiRootView

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("admin/", admin.site.urls),
    path("api/", include("routing.urls")),
]
