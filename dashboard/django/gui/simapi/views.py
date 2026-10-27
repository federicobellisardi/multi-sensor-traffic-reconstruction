from django.shortcuts import render
from django.http import JsonResponse, HttpResponse

import logging
import json
import os
import sys
from datetime import datetime
import threading
from multiprocessing import Process
import time

# libraries
try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'python', 'webservice'))
  from conf import conf
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation
except Exception as e:
  raise Exception('library loading error : {}'.format(e)) from e

# Get logger
logger = logging.getLogger(__name__)

def simulation_task(sim_uid, simc):
  basename = simc["state_basename"]
  logger.info(f'sim uid : {sim_uid}')
  try:
    json.dump(simc, open(basename + '.json', 'w'), indent=2)
    confs = json.dumps(simc)
    logger.info(f'pre')
    s = simulation(confs)
    logger.info(f'sim info : {s.sim_info()}')
    if s.is_valid():
      tsim = datetime.now()
      s.run()
      logger.info(f'simulation done in {datetime.now() - tsim}')
    else:
      logger.info(f'simulation failed')
  except Exception as e:
    logger.info(f'Error in process : {e}')


# Create your views here.
def sapi_sim(request):
  logger.info(f'Request from : {request}')

  if request.method == 'POST':
    body = json.loads(request.body)

    user_start = body['start_date']
    start_date = user_start[:10] + ' 00:00:00'

    stop_date = body['stop_date']

    if user_start >= stop_date:
      logger.error(f'Invalid params user_start ({user_start}) > stop_date ({stop_date})')
      return HttpResponse('Start datetime must be lower than stop datetime', status=500)

    if start_date >= stop_date:
      logger.error(f'Invalid params start_date ({start_date}) > stop_date ({stop_date})')
      return HttpResponse(f'Stop datetime must be strictly higher than {start_date[10:]}', status=500)

    sampling_dt = body['sampling_dt']
    logger.info(f'Parameters {start_date} - {stop_date} sampling {sampling_dt} user_start {user_start}')

    sim_uid = int(datetime.now().strftime('%y%m%d%H%M%S%f'))

    # init conf
    try:
      cfg_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'conf', 'config.json')
      with open(cfg_file) as cin: cfg = json.load(cin)
      cw = conf(cfg)
    except Exception as e:
      logger.error(f'conf init failed : {e}')
      return HttpResponse(f'Conf init failed : {e}', status=500)

    # generate simulation config file
    try:
      simc = cw.generate(start_date, stop_date, sim_uid)
      real_score = cw.real_score
    except Exception as e:
      logger.error(f'conf generation failed : {e}')
      return HttpResponse(f'Conf generation failed : {e}', status=500)

    t = threading.Thread(target=simulation_task, args=(sim_uid, simc, ), daemon=True)
    t.start()

    # p = Process(target=simulation_task, args=(sim_uid, simc, ))
    # p.daemon = True
    # p.start()

    #time.sleep(5)
    logger.info(f'Simulation id {sim_uid} started')


  ret = dict(msg='sim')
  return JsonResponse(ret)

def sapi_check(request):
  ret = dict(msg='check')
  return JsonResponse(ret)
