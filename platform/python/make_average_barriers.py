#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import argparse
import glob
import json
import os
import sys
from datetime import datetime

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'platform', 'python', 'webservice'))
  from conf import conf

except Exception as e:
  raise Exception(f'library loading error : {e}')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', help='generation json config file', required=True)
  parser.add_argument('-wr', '--without_rnd', help='generation json config file without rnd sources', action ='store_true')
  parser.add_argument('-r', '--run', help='run simulation', action='store_true')
  args = parser.parse_args()

  with open(args.config, encoding='utf-8') as cin:
    conf_in = json.load(cin)

  short_fmt = '%y%m%d_%H%M%S'
  date_fmt = '%Y-%m-%d %H:%M:%S'
  conf_in["random"] = args.without_rnd
  sim_times = conf_in['sim_times']


  sched = []
  for start_date, stop_date in sim_times:
    conf_in['start_date'] = start_date
    conf_in['stop_date'] = stop_date
    cfg = conf(conf_in)
    sched.append(cfg.generate_base(start_date, stop_date))

  for simtemplate in sched:
    # create local reduced version of coils geodata file and counter data
    start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
    stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

    avbartag = 'barriers-average'
    if not os.path.exists(avbartag): os.mkdir(avbartag)

    simtemplate['state_basename'] = f'barriers-average/{start.weekday()}'
    simtemplate['enable_stats'] = False
    simtemplate['enable_population'] = False
    simtemplate['enable_influxgrid'] = False

    # run simulation
    if args.run:
      confs = json.dumps(simtemplate)
      s = simulation(confs)
      print('sim info : {}'.format(s.sim_info()))
      if s.is_valid():
        tsim = datetime.now()
        s.run()
        print(f'Sim done in {datetime.now() - tsim}')

  ## JOIN BARRIERS FILES ###
  datafiles = sorted(glob.glob(f'{avbartag}/*_barriers*.csv'))

  df_tot = pd.DataFrame()
  for f in datafiles:
    df = pd.read_csv(f, sep=';')
    n_day = datetime.strptime(df['datetime'].iloc[0], '%Y-%m-%d %H:%M:%S').weekday()
    df['n_wday'] = n_day
    df_tot = pd.concat([df_tot, df])

  df_tot.to_csv(f'{avbartag}/{avbartag}.csv', index=False)


