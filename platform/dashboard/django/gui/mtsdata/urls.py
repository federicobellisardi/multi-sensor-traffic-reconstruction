from django.urls import path

from .views import (
  mts_view,
  mts_cluster,
  mts_ranking,
  mts_forecast,
)

app_name = 'mtsdata'

urlpatterns = [
  path('', mts_view, name='mts_view'),
  path('cluster/', mts_cluster, name='mts_clu'),
  path('ranking/', mts_ranking, name='mts_rank'),
  path('forecast/', mts_forecast, name='mts_forecast'),
]
