import multiprocessing
import time
from datetime import datetime
import logging
import os
import json
import sys

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation
except Exception as e:
  print(f'error in loading simulation python wrapper : {e}')

def simulation_task(sim_uid, simc):
  basename = simc["state_basename"]

  # set up local logger
  logfile = open(f'{basename}.log', 'w', buffering=1)
  logfile.write(f'sim basename {basename}\n')

  try:
    json.dump(simc, open(basename + '.json', 'w'), indent=2)
    confs = json.dumps(simc)
    s = simulation(confs)
    logfile.write(f'sim info : {s.sim_info()}\n')
    if s.is_valid():
      tsim = datetime.now()
      s.run()
      logfile.write(f'simulation done in {datetime.now() - tsim}\n')
    else:
      logfile.write(f'simulation failed')
  except Exception as e:
    logfile.write(f'Error in process : {e}')

  logfile.close()
