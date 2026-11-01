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

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep','python'))
  from config import config

except Exception as e:
  raise Exception(f'library loading error : {e}')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--conf', help='config template', required=True)
  parser.add_argument('-o', '--outdir', help='outdir for config file', required=True)
  parser.add_argument('-m', '--mode', choices=['all','matched'], default='all')
  parser.add_argument('-mf', '--matchfile', help='file of match coils-od')
  parser.add_argument('-wr', '--without_rnd', help='generate json config withour rnd sources', action = 'store_true')

  args = parser.parse_args()

  outdir = args.outdir
  short_fmt = '%y%m%d_%H%M%S'
  date_fmt = '%Y-%m-%d %H:%M:%S'
  without_rnd = args.without_rnd

  with open(args.conf, encoding='utf-8') as cin:
    conf = json.load(cin)

  activity_file = os.path.join(conf['od_average_dir'], 'city_activity.csv')
  activity_prov_file = os.path.join(conf['od_average_dir'], 'prov_activity.csv')
  num_city = conf['num_city']

  ### select City of interest
  df_city = pd.read_csv(activity_file, sep=';')
  df_city = df_city.iloc[:int(num_city)]
  act_id = [str(item).zfill(9) for item in df_city['id']]
  df_city['id'] = act_id

  ### select prov of interest

  df_prov = pd.read_csv(activity_prov_file, sep=';')
  act_prov_id = [str(item).zfill(9) for item in df_prov['id']]
  df_prov['id'] = [ap[3:] for ap in act_prov_id]
  name_prov_outER = df_prov[df_prov['id'].astype(str).str[0:3]!='008'].name.to_list()

  if not os.path.exists(outdir): os.mkdir(outdir)
  city_list = list(df_city['name'])
  prov_list = list(df_prov['name'])

  if args.mode == 'all':

    ### city-city sources ###
    list_pair = list(permutations(city_list, 2))
    val_aug = 10.0
    n=1
    for p in list_pair:
      print(f'city-city: {n}/{len(list_pair)}')
      n+=1
      aug_name = f'{p[0]}_{p[1]}'
      conf['augmentation'] = {aug_name: val_aug}
      conf['random'] = without_rnd
      cfg = config(conf)
      sched = []
      sched.extend(cfg.schedule_tot())

      for dfsrc, simtemplate in sched:
        start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
        stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

        timetag = simtemplate['timetag']
        del simtemplate['timetag']
        tag = simtemplate['tag']
        del simtemplate['tag']

        simconftag = f'{tag}_{timetag}_{p[0]}_{p[1]}'
        #if not os.path.exists(simconftag): os.mkdir(simconftag)

        simconffile = f'{outdir}/{simconftag}.json'
        with open(simconffile,  'w') as sout:
          json.dump(simtemplate, sout, indent=2)


    conf['augmentation'] = {}
    ### prov-prov sources ###
    list_pair_prov = list(permutations(prov_list, 2))
    val_aug = 10.0
    n=1
    for p in list_pair_prov:
      print(f'prov-prov: {n}/{len(list_pair_prov)}')
      n+=1
      id_o = df_prov[df_prov.name == p[0]]['id'].values[0][0:3]
      id_d = df_prov[df_prov.name == p[1]]['id'].values[0][0:3]
      if id_o == id_d:
        continue
      aug_name = f'{p[0]}_{p[1]}'
      conf['augmentation_prov'] = {aug_name: val_aug}
      conf['random'] = without_rnd
      cfg = config(conf)
      sched = []
      sched.extend(cfg.schedule_tot())

      for dfsrc, simtemplate in sched:
        start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
        stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

        timetag = simtemplate['timetag']
        del simtemplate['timetag']
        tag = simtemplate['tag']
        del simtemplate['tag']

        simconftag = f'{tag}_{timetag}_{p[0]}_{p[1]}'
        #if not os.path.exists(simconftag): os.mkdir(simconftag)

        simconffile = f'{outdir}/{simconftag}.json'
        with open(simconffile,  'w') as sout:
          json.dump(simtemplate, sout, indent=2)

  if args.mode == 'matched':

    try:
      df_match = pd.read_csv(args.matchfile, sep=';')
    except Exception as e:
        print(f'Problem with match file : {e}')
        exit(8)

    df_match['is_prov'] = [1 if (r['O'] in name_prov_outER or r['D'] in name_prov_outER) else 0 for i,r in df_match.iterrows()]

    list_value = np.arange(1.0,12.0, 2.0)
    num_total = len(list_value)*len(df_match)

    df_match_city = df_match[df_match.is_prov==0]
    df_match_prov = df_match[df_match.is_prov==1]

    n=0
    ### city-city sim ###
    for i in np.arange(0, len(df_match_city)):
      df_line = df_match_city.iloc[i]
      for j in list_value:
        print(f'city-city: {n}/{num_total}')
        n+=1
        orig = df_line['O']
        dest = df_line['D']
        coil = df_line['Coil']
        aug_name = f'{orig}_{dest}'
        conf['augmentation'] = {aug_name: j}
        conf['random'] = without_rnd
        cfg = config(conf)
        sched = []
        sched.extend(cfg.schedule_tot())

        for dfsrc, simtemplate in sched:
          start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
          stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

          timetag = simtemplate['timetag']
          del simtemplate['timetag']
          tag = simtemplate['tag']
          del simtemplate['tag']

          simconftag = f'{tag}_{timetag}_{coil}_{j}'

          simconffile = f'{outdir}/{simconftag}.json'
          with open(simconffile,  'w') as sout:
            json.dump(simtemplate, sout, indent=2)


    ### prov-prov sim ###
    for i in np.arange(0, len(df_match_prov)):
      df_line = df_match_prov.iloc[i]
      for j in list_value:
        print(f'prov-prov: {n}/{num_total}')
        n+=1
        orig = df_line['O']
        dest = df_line['D']
        coil = df_line['Coil']
        aug_name = f'{orig}_{dest}'
        conf['augmentation_prov'] = {aug_name: j}
        conf['random'] = without_rnd
        cfg = config(conf)
        sched = []
        sched.extend(cfg.schedule_tot())

        for dfsrc, simtemplate in sched:
          start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
          stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

          timetag = simtemplate['timetag']
          del simtemplate['timetag']
          tag = simtemplate['tag']
          del simtemplate['tag']

          simconftag = f'{tag}_{timetag}_{coil}_{j}'

          simconffile = f'{outdir}/{simconftag}.json'
          with open(simconffile,  'w') as sout:
            json.dump(simtemplate, sout, indent=2)









