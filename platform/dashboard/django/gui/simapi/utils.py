from datetime import datetime
import os
import json
import sys

import logging

try:
  sys.path.append(os.path.join(os.environ['WORKSPACEXXX'], 'covid_hep', 'bin'))
  from pysim import simulation
except Exception as e:
  print(f'error in loading simulation python wrapper : {e}')

def simulation_task(sim_uid, simc):
  basename = simc["state_basename"]

  logger = logging.getLogger(f'{__name__}-{sim_uid}')
  logger.info(f'sim basename {basename}')

  try:
    json.dump(simc, open(basename + '.json', 'w'), indent=2)
    confs = json.dumps(simc)
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
