from django.contrib import admin
from django.urls import path

from .views import (
  submit_view,
  simulation_view,
  simulation_detail,
  simulation_uid_detail,
  sim_post,
  status_get,
  geojson_get,
  view_playground,
  carto_view,
  result_csv,
  simulation_fluxes,
)

app_name = 'dashboard'

urlpatterns = [
  path('admin/', admin.site.urls),
  path('', submit_view, name='submit'),
  path('carto', carto_view, name='carto'),
  path('sim/', sim_post, name='sim_forward'),
  path('status/<sim_uid>', status_get, name='sim_status'),
  path('poly/', geojson_get, name='poly_forward'),
  path('simulations/', simulation_view, name='sim_view'),
  path('simulations/<sim_id>', simulation_detail, name='sim_detail'),
  path('simulations/uid/<sim_uid>', simulation_uid_detail, name='simuid_detail'),
  path('simulations/fluxes/<sim_id>', simulation_fluxes, name='simulation_fluxes'),
  path('simulations/result/<sim_id>', result_csv, name='result_csv'),
  path('gardaland', view_playground, name='playgr'),
]
