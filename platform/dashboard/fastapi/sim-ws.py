# launch with
# uvicorn simulation-ws:app --reload --port 9999

# and test with
# GET test
# curl --request GET http://localhost:9999
# POST test
# curl --header "Content-Type: application/json" --request POST --data '{"key": "value"}' http://localhost:9999/...

import sys
import os
import json
from datetime import datetime
import pandas as pd
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Response
from pydantic import BaseModel, Field, validator
import logging
import glob
import time
import pytz

import threading
from multiprocessing import Process

###############
### version ###
###############
if 'MOVER_VERSION' in os.environ:
  ver = os.environ['MOVER_VERSION']
else:
  ver = 'local'

#################
### libraries ###
#################
try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'platform', 'dashboard', 'fastapi', 'python'))
  from conf import conf
  from simulation import simulation_task
  from correction import SimPostCorrection
  #from security import *

except Exception as e:
  raise Exception('library loading error : {}'.format(e)) from e

# init
tags_metadata = [
  {
    "name" : "welcome",
    "description": "Welcome API."
  },
  {
      "name": "sim",
      "description": "Simulation API.",
  },
  {
      "name": "status",
      "description": "Progress and results collection API.",
  },
]

app = FastAPI(
  title="fluxes simulator",
  description="A web api providing mobility prediction algorithm",
  version=ver,
  openapi_tags=tags_metadata
)

class response_welcome(BaseModel):
  message : str = 'simulation ws'
  version : str = ver

class response_sim(BaseModel):
  message : str = 'simulation OK'
  sim_uid  : str = 'noid'
  real_score : float = 0
  user_start : str = ''

class response_poly(BaseModel):
  message : str = 'geojson OK'
  geojson : dict = {}

class body_sim(BaseModel):
  start_date : str
  stop_date : str
  sampling_dt : int

class response_status(BaseModel):
  sim_uid : str
  status : str
  elapsed : int = 0
  completion : float = 0
  results : Optional[dict]

#################
#### APIs ####
#################

DEFAULT_GRID_SIZE = 100

@app.on_event("startup")
async def startup_event():
  global logger

  if ver == 'local':
    import coloredlogs

    log_folder = '../logs'
    if not os.path.exists(log_folder): os.mkdir(log_folder)

    # config logger
    console_formatter = coloredlogs.ColoredFormatter('%(asctime)s [%(levelname)s] (%(name)s:%(funcName)s) %(message)s', "%H:%M:%S")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s:%(funcName)s) %(message)s', "%y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(f'{log_folder}/sim_ws.log')
    file_handler.setFormatter(file_formatter)

    # clear uvicorn logger
    logging.getLogger("uvicorn").handlers.clear()
    access_log = logging.getLogger("uvicorn.access")
    access_log.handlers.clear()
    access_log.addHandler(console_handler)
    access_log.addHandler(file_handler)

    logging.basicConfig(
      level=logging.DEBUG,
      handlers=[
        file_handler,   # log file handler
        console_handler # console stream handler
      ]
    )
  else:
    log_folder = '/output/logs'
    if not os.path.exists(log_folder): os.makedirs(log_folder)

    time_formatter = logging.Formatter('%(asctime)s [%(process)d] [%(levelname)s] (%(name)s) %(message)s', "%y%m%d %H:%M:%S")
    time_handler = logging.FileHandler(f'{log_folder}/sim_ws.log')
    time_handler.setFormatter(time_formatter)

    logging.basicConfig(
      level=logging.DEBUG,
      handlers=[
        time_handler
      ]
    )

  logging.getLogger('matplotlib').setLevel(logging.WARNING)
  logging.getLogger('urllib3').setLevel(logging.WARNING)
  logging.getLogger('shapely').setLevel(logging.WARNING)
  logging.getLogger('passlib').setLevel(logging.WARNING)
  logging.getLogger('multipart').setLevel(logging.WARNING)
  logging.getLogger('fiona').setLevel(logging.WARNING)
  logger = logging.getLogger('mover')
  logger.info(f'Setting logger config for version : {ver}')

@app.get('/',
  response_model=response_welcome,
  tags=['welcome']
)
async def root():
  return response_welcome()

@app.post(
  '/sim',
  response_model=response_sim,
  tags=['sim']
)
async def sim_post(body: body_sim, request: Request):
  client_ip = request.client.host
  logger.info(f'Request from {client_ip} '.format())

  user_start = body.start_date
  start_date = user_start[:10] + ' 00:00:00'

  stop_date = body.stop_date

  if user_start >= stop_date:
    logger.error(f'Invalid params user_start ({user_start}) > stop_date ({stop_date})')
    raise HTTPException(status_code=500, detail='Start datetime must be lower than stop datetime')

  if start_date >= stop_date:
    logger.error(f'Invalid params start_date ({start_date}) > stop_date ({stop_date})')
    raise HTTPException(status_code=500, detail=f'Stop datetime must be strictly higher than {start_date[10:]}')

  sampling_dt = body.sampling_dt
  logger.info(f'Parameters {start_date} - {stop_date} sampling {sampling_dt} user_start {user_start}')

  sim_uid = os.getpid()
  sim_uid = datetime.now().strftime('%y%m%d%H%M%S%f')
  logger.debug(f'Simulation UID : {sim_uid}')

  # init conf
  try:
    cfg_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'conf', 'config.json')
    with open(cfg_file) as cin: cfg = json.load(cin)
    cw = conf(cfg)
  except Exception as e:
    logger.error(f'conf init failed : {e}')
    raise HTTPException(status_code=500, detail=f'Conf init failed : {e}')

  # generate simulation config file
  try:
    simc = cw.generate(start_date, stop_date, sim_uid)
    real_score = cw.real_score
  except Exception as e:
    errormsg = f'Conf generation failed : {e}'
    logger.error(errormsg)
    raise HTTPException(status_code=500, detail=errormsg)

  p = Process(target=simulation_task, args=(sim_uid, simc, ))
  p.daemon = True
  p.start()

  time.sleep(5)
  logger.info(f'Simulation id {sim_uid} started')

  ret = response_sim(
    message='simulation submitted',
    sim_uid=sim_uid,
    real_score=real_score,
    user_start=user_start
  )

  return ret

@app.get('/poly',
  response_model=response_poly,
  tags=['poly']
)
async def poly_get(request: Request):
  client_ip = request.client.host
  logger.info(f'Request from {client_ip}'.format())

  # init conf
  try:
    cfg_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'conf', 'config.json')
    with open(cfg_file) as cin: cfg = json.load(cin)
    cw = conf(cfg)

  except Exception as e:
    logger.error(f'conf generation failed : {e}')
    raise HTTPException(status_code=500, detail='grid geojson conf init failed : {}'.format(e))

  wdir = cw.wdir
  with open(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'templates', 'check_template.json')) as cin : simconf = json.load(cin)
  confs = json.dumps(simconf)

  s = simulation(confs)
  logger.info(f'simulation info\n{s.sim_info()}')

  if s.is_valid():
    try:
      base =  wdir + '/poly'
      geojf = base + '.geojson'
      s.dump_poly_geojson(base)
      with open(geojf) as gin:
        geoj = json.load(gin)
      ret = response_poly(
        message=f'geojson version {ver}',
        geojson=geoj
      )
    except Exception as e:
      logger.error(f'poly geojson exc : {e}')
      raise HTTPException(status_code=500, detail='poly geojson exc : {}'.format(e))
  else:
    raise HTTPException(status_code=501, detail='poly geojson creation failed')

  return ret


@app.get(
  '/status/{sim_uid}',
  response_model=response_status,
  tags=['status']
)
async def status_get(request: Request, sim_uid: str, download: bool = False, user_start: str = '', mode='json', correction_mode: str = 'default'):
  # init conf
  try:
    cfg_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'conf', 'config.json')
    with open(cfg_file) as cin: cfg = json.load(cin)
    cw = conf(cfg)
  except Exception as e:
    logger.error(f'conf init failed : {e}')
    raise HTTPException(status_code=500, detail=f'conf init failed : {e}')

  sim_basename = cw.get_basename(sim_uid)
  statusfile =  sim_basename + '.status'
  # print(statusfile)
  if os.path.exists(statusfile):
    logger.info(f'status file exists')
    res = response_status(sim_uid=sim_uid, status='running')
    try:
      status = pd.read_csv(statusfile, sep=';', parse_dates=['datetime']).sort_values(by='index')
      # print(status)
      idx0, tot0, ts0 = status.iloc[0].values
      idx, tot, ts = status.iloc[-1].values
      # print(idx, tot, ts)
      elapsed = (ts-ts0).total_seconds()
      if idx == tot:
        if download:
          logger.info(f'Correction mode is: {correction_mode}')
          if user_start != '':
            user_t = pd.to_datetime(user_start).tz_localize(pytz.timezone('Europe/Rome'))

          simco = SimPostCorrection(cfg, sim_basename)
          if correction_mode == 'default':
            try:
              datafile = simco.correct()
            except Exception as e:
              logger.error(f'Corrections failed : {e}')
              datafile = glob.glob(f'{sim_basename}_uniq*.csv')
              datafile = datafile[0] if len(datafile) == 1 else 'no_file'
            df = pd.read_csv(datafile, sep=';', index_col=['poly_lid', 'poly_cid', 'oneway']).T
            # df = df.T
            df.index = pd.to_datetime(df.index).tz_localize(pytz.timezone('Europe/Rome'))
            # df = df[ df.index >= user_t ]
            df = df.droplevel(['poly_cid', 'oneway'], axis=1)
            df = df.groupby(level=0, axis=1).sum()

            if mode == 'json':
              df.index = [ f'{t}' for t in df.index ]
              dfstring = f'{df.to_json(orient="index")}'
              result = {'jsondata': dfstring}
            elif mode == 'csv':
              df = df.stack().reset_index()
              df.columns = ['datetime', 'poly_lid', 'counter']
              df = df[['poly_lid', 'datetime', 'counter']].set_index('poly_lid')
              df['counter'] = df['counter'].astype(int)
              result = {'csvdata': f'{df.to_csv(sep=",")}'}

          elif correction_mode == 'delta_std':
            try:
              datafile = simco.correct_prov()
              df = pd.read_csv(datafile, sep=';')
              if mode == 'csv':
                result = {'csvdata': f'{df.to_csv(sep=",")}'}
            except Exception as e:
              logger.error(f'Correction failed: {e}')

          else:
            raise HTTPException(status_code=404, detail=f'Invalid correction mode : {correction_mode}')

          if cw.remove_local_output:
            garbage = glob.glob(f'{sim_basename}*')
            for trash in garbage:
              os.remove(trash)
            #print(garbage)

          logger.info(f'sim download : dowload {download} mode {mode} cleanup {cw.remove_local_output}')
          res = response_status(sim_uid=sim_uid, status='complete', completion=1.0, results=result, elapsed=elapsed)
        else:
          logger.info(f'sim progress : completion=1, elapsed={elapsed}')
          res = response_status(sim_uid=sim_uid, status='complete', completion=1.0, elapsed=elapsed)
      else:
        logger.info(f'sim progress : completion={idx/tot:.3f}, elapsed={elapsed}')
        res = response_status(sim_uid=sim_uid, status='running', completion=idx/tot, elapsed=elapsed)
    except Exception as e:
      logger.error(f'error reading status : {e}')
      res = response_status(sim_uid=sim_uid, status='error', completion=0)
  else:
    logger.warning(f'status file does not exists')
    res = response_status(sim_uid=sim_uid, status='invalid sim_uid')
    #time.sleep(1)
  return res

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, port=9000)
