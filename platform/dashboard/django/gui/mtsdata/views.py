from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import random

from .utils import mts

# Create your views here.
@login_required
def mts_view(request):
  if request.method == 'GET':
    coil_id = request.GET.get('coil_id')
  if coil_id is None:
    coil_id = '282'

  # validation
  mtsval = mts.validation()

  validation = dict (
    mtsval = mtsval,
    daysize = 286 * 2 * 96
  )

  # series data
  # start_date = '2021-05-24 00:00:00'
  # stop_date = '2021-06-01 00:00:00'
  start_date = '2022-09-01 00:00:00'
  stop_date = '2022-09-30 23:59:59'

  try:
    mtsseries = mts.series(coil_id, start_date, stop_date)

    coils = dict(
      coil_id = coil_id,
      start_date = start_date,
      stop_date = stop_date,
      mtsseries = mtsseries,
    )
  except Exception as e:
    print(f'Exception: {e}')
    coils = dict(
      coil_id = coil_id,
      start_date = start_date,
      stop_date = stop_date,
      mtsseries = None,
    )

  # map data
  coil_pos, coil_pro = mts.get_coil_loc(coil_id)
  geodata = {
    'data' : {
      f'Coil_{coil_id}': {
      'color' : 'red',
      'data': [
        [ coil_pos , f'Coil id : <b>{coil_id}</b><br>Province : <b>{coil_pro}</b>'],
       ]
      },
    }
  }

  # render page
  context = dict (
    coils = coils,
    validation = validation,
    geodata = geodata,
    coilid = mts.coilid,
  )
  return render(request, 'mtsdata/mts_view.html', context)

def mts_cluster(request):
  geodata = mts.get_coil_cluster()
  context = dict ( geodata = geodata )
  return render(request, 'mtsdata/mts_cluster.html', context)

def mts_ranking(request):
  if request.method == 'GET':
    pro_tag = request.GET.get('pro_tag')
  if pro_tag is None: pro_tag = 'BO'

  # validation
  mtsval = mts.validation()

  validation = dict (
    mtsval = mtsval,
    daysize = 286 * 2 * 96
  )

  # ranking
  ranking, geodata = mts.get_ranking(pro_tag)

  # render page
  context = dict (
    validation = validation,
    pro_tag=pro_tag,
    ranking=ranking,
    pro = mts.pro,
    geodata=geodata,
  )
  return render(request, 'mtsdata/mts_ranking.html', context)

def mts_forecast(request):
  if request.method == 'GET':
    coil_id = request.GET.get('coil_id')
  if coil_id is None:
    coil_id = '182'

  # best_model_compute = mts.get_best_model(coil_id)
  # mtsforecast = mts.coil_forecast(coil_id)

  mtslocalanomaly = mts.localanomaly(coil_id)

  context = dict (
    mtslocalanomaly = mtslocalanomaly
  )

  return render(request, 'mtsdata/mts_forecast.html', context)

