import time
from datetime import datetime
import logging

def func():
  return 42

def get_task_statufile(sim_uid):
  return f'sim_{sim_uid}.status'

# CPP PLACEHOLDER
innner_tick = 0.1
nstep = 80
def fake_cpp_task(sim_uid):
  logger = logging.getLogger(f'sim_task_{sim_uid}')
  statusfile = get_task_statufile(sim_uid)
  statusf = open(statusfile, 'w')
  statusf.write(f'index/nstep/timestamp\n')
  statusf.close()
  for i in range(nstep+1):
    time.sleep(innner_tick)
    statusf = open(statusfile, 'a')
    logger.warning(f'{i}/{nstep}/{datetime.now()}')
    statusf.write(f'{i}/{nstep}/{datetime.now()}\n')
    statusf.close()
    #print(f'{i}/{nstep} {datetime.now()}')