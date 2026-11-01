#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
import json
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
import multiprocessing as mp
from multiprocessing import Pool
import matplotlib.pyplot as plt
import glob

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation
except Exception as e:
  raise Exception('library loading error : {}'.format(e)) from e

def run_simulation(param_list):
  simid = param_list[0]
  simconf = param_list[1]
  print(f'start sim {simid:04d}', flush=True)
  tnow = datetime.now()
  nthread = simconf['n_thread']
  s = simulation(json.dumps(simconf))
  print(f'sim {simid:04d} info : {s.sim_info()}')
  s.run()
  simtime = datetime.now() - tnow
  print(f'sim {simid:04d} took : {simtime}')
  return (simid, int(1000*simtime.total_seconds()), nthread)

if __name__ == '__main__':
  # parse cli and config
  parser = argparse.ArgumentParser()
  parser.add_argument('-w', '--workdir', help='output directory', required=True)
  parser.add_argument('-c', '--confdir', help='sim config scan input directory', default='simconf')
  parser.add_argument('-g', '--go', help='run scan', action='store_true')
  parser.add_argument('-ms', '--maxsim', help='override max sim number', type=int, default='-1')
  parser.add_argument('-n', '--nthread', help='number of opemnp core to use for parallel scan', type=int, default=-1)
  parser.add_argument('-a', '--nagents', help='number of mp agents to use for parallel scan', type=int, default=1)
  args = parser.parse_args()

  wdir = args.workdir
  if not os.path.exists(wdir): os.mkdir(wdir)
  csvdir = f'{wdir}/csv'
  if not os.path.exists(csvdir): os.mkdir(csvdir)
  confdir = f'{wdir}/conf'
  if not os.path.exists(confdir): os.mkdir(confdir)

  varsdir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars')

  """
  Run simulation from folder
  """
  inputdir = args.confdir
  maxsim = args.maxsim
  go = args.go
  nproc = mp.cpu_count()
  nth = args.nthread
  if nth == -1: nth = nproc
  nagents = args.nagents

  fileconf = glob.glob(f'{inputdir}/*.json')
  fileconf = sorted(fileconf)
  if maxsim > 0:
    fileconf = fileconf[:maxsim]
  schedule = { i : json.load(open(f)) for i,f in enumerate(fileconf) }

  schedule_name = {i: os.path.basename(f)[:-5] for i, f in enumerate(fileconf)}
  sched_para = { k:v for k,v in schedule.items() }

  for i in sched_para:
    sched_para[i]['file_pro']     = f'{varsdir}/carto/er-speed.pro'
    sched_para[i]['file_pnt']     = f'{varsdir}/carto/er-speed.pnt'
    sched_para[i]['file_barrier'] = f'{varsdir}/extra/er_barriers.csv'
    sched_para[i]['file_score_pop'] = f'{varsdir}/extra/ace_score.csv'
    sched_para[i]['n_thread'] = nth
    sched_para[i]['state_basename'] = f'{csvdir}/{schedule_name[i]}'
    del sched_para[i]['enable_stats']
    del sched_para[i]['enable_population']
    print(schedule_name[i])
    json.dump(sched_para[i], open(f'{confdir}/{schedule_name[i]}.json', 'w'), indent=2)
  nsim = len(sched_para)
  chunksize = nsim // nagents

  print(f'Simulation number  : {nsim}')
  print(f'Number of thread   : {nproc}')
  print(f'OMP thread per sim : {nth}')
  print(f'Agents             : {nagents}')
  print(f'Chunksize          : {chunksize}')
  print(f'Check              : chunksize*nagents >= nsim ? {chunksize*nagents >= nsim}')

  if go:
    tnow = datetime.now()
    with Pool(processes=nagents) as pool:
      result = pool.map(run_simulation, sched_para.items(), chunksize)
    tscan = datetime.now() - tnow
    print(f'Scan took {tscan}')

    dfstats = pd.DataFrame(result, columns=[
      'simid',
      'simtime',
      'n_thread'
    ])
    dfstats.to_csv(f'{wdir}/stats_p.csv', sep=';', index=False)
