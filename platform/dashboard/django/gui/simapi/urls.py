from django.urls import path

from .views import (
  sapi_sim,
  sapi_check,
)

app_name = 'simapi'

urlpatterns = [
  path('sim/', sapi_sim, name='sim'),
  path('check/', sapi_check, name='check'),
]
