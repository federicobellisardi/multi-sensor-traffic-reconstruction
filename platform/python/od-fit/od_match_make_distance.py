#! /usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob
import numpy as np
import argparse
from itertools import permutations
import sys

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-s0', '--syn0', help='file barriers withour augm', required=True)
  parser.add_argument('-d', '--dir', help='directory with file barriers augmented', required=True)
  args = parser.parse_args()

  ra_tresh=2.0

  # read coils geodata
  barfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
  dfbar = pd.read_csv(barfile, sep=';')
  dfbar = dfbar.drop(columns='Description').set_index('ID')

  # read coil dir mappings
  dirmapfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_spire', 'coils-dir-mapping_template_0.50.csv')

  selcoil = pd.read_csv(dirmapfile, sep=';', comment='#')
  #print(f'**** NB manually dropped coils : {manual_drop_list}')
  manual_drop_list = [177]
  selcoil = selcoil[ ~selcoil.coil_id.isin(manual_drop_list)]
  coil_list = selcoil.coil_id.to_numpy()

  # create direction dict for matching and filtering
  sel_coildir = [ f'{cid}_IN' for cid in selcoil.coil_id.values ]
  sel_coildir.extend([ f'{cid}_OUT' for cid in selcoil.coil_id.values ])
  sel_coildir = sorted(sel_coildir)


  dfsyn0 = pd.read_csv(args.syn0, sep=';', parse_dates=['datetime']).set_index('datetime')
  start = dfsyn0.index.min()
  stop = dfsyn0.index.max() # this must be included
  dfsyn0 = dfsyn0[dfsyn0.columns.intersection(sel_coildir)]

  # initialize collector
  match_collection={}
  for s in sel_coildir:
    match_collection[s]=[]

  file_list = [f for f in os.listdir(args.dir) if os.path.isfile(os.path.join(args.dir, f))]
  for f in file_list:
    dfsyn = pd.read_csv(os.path.join(args.dir, f), sep=';', parse_dates=['datetime']).set_index('datetime')
    dfsyn = dfsyn[dfsyn.columns.intersection(sel_coildir)]

    for c in sel_coildir:
      v0   = dfsyn0[c].to_numpy()
      vsyn = dfsyn[c].to_numpy()

      ### metric: area ratio
      asyn = vsyn.sum()
      a0 = v0.sum()
      if a0==0:
        ratio = 0
      else:
        ratio =asyn/a0

      name_o = f.split('_')[5]
      name_d = f.split('_')[6]
      str_od = f'{name_o}_{name_d}'
      match_collection[c].append({'name':str_od, 'ra':ratio})

  list_names =  ['Coil','O','D','ra']
  df_coll = pd.DataFrame(columns=list_names)
  for mc, ml in match_collection.items():
    match_collection[mc] = sorted(ml, key=lambda k: k['ra'], reverse=True)
    first = match_collection[mc][0]
    print(mc, first)
    if abs(first['ra']) > ra_tresh:
      orig, dest = first['name'].split('_')
      df_line = pd.DataFrame([[mc, orig, dest, first['ra']]], columns=list_names)
      df_coll = df_coll.append(df_line, ignore_index=True)

  df_coll.to_csv('matched.csv', sep=';', index=False)
