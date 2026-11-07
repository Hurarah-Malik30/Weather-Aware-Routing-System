from django.urls import path

from .views import HealthView, HeatmapPointsView, HeatmapView, RoutesView, ScoreView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("routes/", RoutesView.as_view(), name="routes"),
    path("score/", ScoreView.as_view(), name="score"),
    path("heatmap/points/", HeatmapPointsView.as_view(), name="heatmap-points"),
    path("heatmap/", HeatmapView.as_view(), name="heatmap"),
]
