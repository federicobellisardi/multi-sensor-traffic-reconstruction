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

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep','python'))
  from config import config

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'minimocas', 'python', 'tools'))
  from synthvscam_plot import synthvscam_dir, synthvscam_global


except Exception as e:
  raise Exception(f'library loading error : {e}')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', help='generation json config file', required=True)
  parser.add_argument('-mv', '--mv', help='collection of metrics values', required=True)
  parser.add_argument('-mf', '--matchfile', help='file of match and fit', required=True)
  parser.add_argument('-r', '--run', help='run simulation', action='store_true')
  parser.add_argument('-cp', '--coilsplot',help='make coils plot', action='store_true')
  parser.add_argument('-wr', '--without_rnd', help='generate json config withour rnd sources', action = 'store_true')

  args = parser.parse_args()
  without_rnd = args.without_rnd

  with open(args.config, encoding='utf-8') as cin:
    conf = json.load(cin)

  short_fmt = '%y%m%d_%H%M%S'
  date_fmt = '%Y-%m-%d %H:%M:%S'
  polygons_geojson = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-shapes.geojson')

  df_prov = pd.read_csv(os.path.join(conf['od_average_dir'], 'prov_activity.csv'), sep=';')
  act_prov_id = [str(item).zfill(9) for item in df_prov['id']]
  df_prov['id'] = [ap[3:] for ap in act_prov_id]
  name_prov_outER = df_prov[df_prov['id'].astype(str).str[0:3]!='008'].name.to_list()

  df_mv = pd.read_csv(args.mv, sep=';')
  df_match = pd.read_csv(args.matchfile, sep=';')
  df_match['is_prov'] = [1 if (r['O'] in name_prov_outER or r['D'] in name_prov_outER) else 0 for i,r in df_match.iterrows()]

  dict_n_aug = {}
  dict_n_aug_prov = {}
  for i in np.arange(0, len(df_match)):
    df_w = df_match.iloc[i]
    orig = df_w['O']
    dest = df_w['D']
    mv = df_mv[df_mv.Coil == df_w['Coil']].ra.values[0]
    #mv = df_mv[df_mv.Coil == df_w['Coil']].l1.values[0]
    a = df_w['A']
    b = df_w['B']
    #n_aug = (l1 + a)/a
    n_aug = (mv-b)/a
    if df_w['is_prov'] == 0:
      dict_n_aug[f'{orig}_{dest}'] = n_aug
    else:
      dict_n_aug_prov[f'{orig}_{dest}'] = n_aug

  conf['augmentation'] = dict_n_aug
  conf['augmentation_prov'] = dict_n_aug_prov
  conf['random'] = without_rnd
  cfg = config(conf)
  sched = []
  sched.extend(cfg.schedule_tot())

  for dfsrc, simtemplate in sched:
    # create local reduced version of coils geodata file and counter data
    start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
    stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

    timetag = simtemplate['timetag']
    del simtemplate['timetag']
    tag = simtemplate['tag']
    del simtemplate['tag']

    simconftag = f'{tag}_{timetag}'
    if not os.path.exists(simconftag): os.mkdir(simconftag)

    dfdump = dfsrc.copy()
    dfdump.insert(loc=0, column='timestamp', value=[ t.timestamp() for t in dfdump.index ])
    camdata = f'{tag}_{timetag}/{tag}_databarriers_{timetag}.csv'
    dfdump.to_csv(camdata, sep=';')


    simconffile = f'{simconftag}/{simconftag}.json'
    with open(simconffile,  'w') as sout:
      json.dump(simtemplate, sout, indent=2)

    # run simulation
    if args.run:
      confs = json.dumps(simtemplate)
      s = simulation(confs)
      print('sim info : {}'.format(s.sim_info()))
      if s.is_valid():
        tsim = datetime.now()
        s.run()
        print(f'Sim done in {datetime.now() - tsim}')

    if args.coilsplot:
      filter_coils_plot = df_match['Coil'].to_list()

      try:
        sd = start.strftime('%y%m%d_%H%M%S')
        synf = f'{simconftag}/{tag}_barriers_{sd}.csv'
        outpng = f'{simconftag}/{tag}_synthvscam_{sd}.png'

        dirmapfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_spire', 'coils-dir-mapping_template_0.50.csv')
        selcoil = pd.read_csv(dirmapfile, sep=';', comment='#')
        manual_drop_list = [177]
        #print(f'**** NB manually dropped coils : {manual_drop_list}')
        selcoil = selcoil[ ~selcoil.coil_id.isin(manual_drop_list)]

        #print(selcoil)
        coil_list = selcoil.coil_id.to_numpy()
        dir_map = {}
        for i, (cid, dirr, dirc) in selcoil.iterrows():
          #print(i, (cid, dirr, dirc))
          dirr2 = 1 if dirr == 0 else 0
          dirc2 = 'OUT' if dirc == 'IN' else 'IN'
          dir_map[f'{cid}_{dirc}'] = f'{cid}_{dirr}'
          dir_map[f'{cid}_{dirc2}'] = f'{cid}_{dirr2}'

        synthvscam_global(camin=camdata, synin=synf, filter=filter_coils_plot, dir_map=dir_map, outpng=f'{simconftag}/{tag}_synthvscam_global')

        for f in filter_coils_plot:
          synthvscam_dir(camin=camdata, synin=synf, filter=[f, dir_map[f]], outpng=f'{simconftag}/{tag}_synthvscam_{sd}_{f}.png')
      except Exception as e:
        print(f'Problems with synthvscam_dir plot : {e}')


