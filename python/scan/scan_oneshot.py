#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import argparse
import glob
import json
import os
import sys
from datetime import datetime

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation
except Exception as e:
  raise Exception(f'library loading error : {e}')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--simid', help='sim_id (0 padded)', required=True)
  parser.add_argument('-d', '--scandir', help='scan output directory', required=True)
  parser.add_argument('-r', '--run', help='run simulation', action='store_true')
  args = parser.parse_args()

  configfile = f'{args.scandir}/conf/{args.simid}_conf.json'
  with open(configfile) as cin:
    simcfg = json.load(cin)

  oneshotdir = 'oneshot'
  if not os.path.exists(f'{oneshotdir}/csv'): os.makedirs(f'{oneshotdir}/csv')
  if not os.path.exists(f'{oneshotdir}/conf'): os.makedirs(f'{oneshotdir}/conf')

  # fix local parameters
  simcfg['file_pro'] = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'carto', 'er-speed.pro')
  simcfg['file_pnt'] = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'carto', 'er-speed.pnt')
  simcfg['file_barrier'] = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
  simcfg['state_basename'] = f'{oneshotdir}/csv/{args.simid}'
  simcfg['n_thread'] = -1

  with open(f'{oneshotdir}/conf/{args.simid}_conf.json', 'w') as cout:
    json.dump(simcfg, cout, indent=2)

  # run simulation
  if args.run:
    confs = json.dumps(simcfg)
    s = simulation(confs)
    print('sim {} info : {}'.format(args.simid, s.sim_info()))
    if s.is_valid():
      tsim = datetime.now()
      s.run()
      print(f'Sim done in {datetime.now() - tsim}')

