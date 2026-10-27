#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os
import json
import argparse
import numpy as np
from itertools import product
from datetime import datetime
import pandas as pd

if __name__ == '__main__':
  # parse cli and config
  parser = argparse.ArgumentParser()
  parser.add_argument('-t', '--template', help='sim config json template', required=True)
  parser.add_argument('-o', '--outdir', help='conf json output directory', required=True)
  parser.add_argument('-n', '--nthread', help='select max number of thread used', type=int, default=-1)
  parser.add_argument('-m', '--mode', choices=['a-b-ttb'], default='a-b-ttb')
  args = parser.parse_args()

  wdir = args.outdir
  if not os.path.exists(wdir): os.mkdir(wdir)

  with open(args.template) as cin:
    conft = json.load(cin)

  """
  alpha-beta-travel_time_budget combinatorics
  """
  if args.mode == 'a-b-ttb':
    beta_r = np.linspace(0.0, 1, 5)
    alpha_r = np.linspace(0.0, 1, 5)
    ttb_r = np.arange(1800.0, 7201.0, 900.0)
    list_comb = list(product(ttb_r, beta_r, alpha_r))

    summary = []
    schedule = {}
    for i, lc in enumerate(list_comb):
      schedule.update({
        i : {
          'b_l' : 0.0,
          'ttb' : lc[0],
          'b'   : lc[1],
          'a'   : lc[2],
        }
      })
      summary.append([ i, *lc, 1-lc[2]])

    dfs = pd.DataFrame(summary, columns=['id', 'ttb', 'b', 'a_w', 'a_s'])
    dfs.to_csv(f'{wdir}_summary.csv', sep=';', index=False)

    for sid, sch in schedule.items():
      conf = { k:v for k,v in conft.items() }

      for s, src in conf["sources"].items():
        for ps, pwn in src.items():
          if ps.startswith("pawn"):
            for pt, pwn_t in pwn.items():
              if pt.startswith("scr_dest"):
                conf["sources"][s][ps][pt]["beta_bp_miss"] = sch['b_l']
                conf["sources"][s][ps][pt]["alpha_we"]     = sch['a']
                conf["sources"][s][ps][pt]["alpha_speed"]  = 1-sch['a']
              else:
                conf["sources"][s][ps][pt]["TTB"]          = sch['ttb']
                conf["sources"][s][ps][pt]["beta_bp_miss"] = sch['b']
                conf["sources"][s][ps][pt]["alpha_we"]     = sch['a']
                conf["sources"][s][ps][pt]["alpha_speed"]  = 1-sch['a']

      # clean up
      if 'state_basename' in conf: conf.pop('state_basename')
      if 'enable_population' in conf: conf.pop('enable_population')
      if 'enable_influxgrid' in conf: conf.pop('enable_influxgrid')
      if 'enable_stats' in conf: conf.pop('enable_stats')
      if 'enable_netstate' in conf: conf.pop('enable_netstate')
      if 'explore_node' in conf: conf.pop('explore_node')
      if 'file_polygons' in conf: conf.pop('file_polygons')
      if 'enable_polygons' in conf: conf.pop('enable_polygons')

      outcfg = f'{wdir}/conf_{sid:04d}.json'
      with open(outcfg, 'w') as cout:
        print(outcfg)
        json.dump(conf, cout, indent=2)

    print(f'Scheduled simulation : {len(schedule)}')

  else:
    raise Exception(f'Mode {args.mode} not implemented')
