from django.conf import settings

import logging
logging.getLogger('fiona').setLevel(logging.WARNING)
logging.getLogger('shapely').setLevel(logging.WARNING)

import geopandas as gpd
from pandas import to_datetime
from requests import post, get
import time
import os
from datetime import datetime, timedelta

from .models import Simulation

class cartodata():

  def __init__(self):
    self.carto_file = f'{settings.DATA_DIR}/carto.geojson'
    df = gpd.read_file(self.carto_file)
    df = df.set_index('poly_lid')
    self.carto = df
    static_carto = f'{settings.SIM_RESULT_DIR}/carto.geojson'
    if not os.path.exists(static_carto):
      df.to_file(static_carto, driver='GeoJSON')

  def get_poly(self, id_list=None):
    if id_list is not None:
      df = self.carto[ self.carto.index.isin(id_list) ]
    else:
      df = self.carto
    return df

carto = cartodata()


def status_update_thread(sim_uid, start_date, correction_mode):
  logger = logging.getLogger('django')

  elaptime = timedelta(seconds=0)
  maxtime = timedelta(seconds=3600)
  tnow = datetime.now()
  user_t = to_datetime(start_date).tz_localize(None).tz_localize('Europe/Rome')

  time.sleep(2)
  while elaptime < maxtime:
    #logger.warning(elaptime)
    elaptime = datetime.now() - tnow
    url = f'http://{settings.SIMWS_BASEURL}/status/{sim_uid}'
    r = get(url)
    ret = r.json()
    # print(ret)
    try:
      if ret['status'] == 'complete':
        logger.debug('Sim complete')
        url1 = f'http://{settings.SIMWS_BASEURL}/status/{sim_uid}?download={True}&user_start={user_t}&mode=csv&correction_mode={correction_mode}'
        r1 = get(url1)
        ret1 = r1.json()
        results_path = f'{settings.SIM_RESULT_DIR}/sim_{sim_uid}.csv'
        with open(results_path, 'w') as rout:
          rout.write(ret1['results']['csvdata'])

        sim = Simulation.objects.get(sim_id=sim_uid)
        sim.results_path = results_path
        sim.runtime = int(ret1['elapsed'])
        sim.completion = ret1['completion']
        sim.status = Simulation.SIM_COMPLETE
        sim.save()

        return
      else:
        sim = Simulation.objects.get(sim_id=sim_uid)
        sim.runtime = int(ret['elapsed'])
        sim.completion = ret['completion']
        sim.save()
    except Exception as e:
      logger.error(f'Killing thread {sim_uid} exc {e}')
      return

    # print(sim)
    time.sleep(1)

  logger.error(f'Thread {sim_uid} timed out start {tnow} elapsed {elaptime}')
