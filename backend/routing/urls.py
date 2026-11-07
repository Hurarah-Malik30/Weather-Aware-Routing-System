from django.urls import path

from .views import HealthView, HeatmapView, PlanView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("plan/", PlanView.as_view(), name="plan"),
    path("heatmap/", HeatmapView.as_view(), name="heatmap"),
]
