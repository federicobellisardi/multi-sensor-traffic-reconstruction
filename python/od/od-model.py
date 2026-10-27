#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import argparse
import glob
import json
import os
import datetime
from datetime import datetime

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--dir', help='dir of od csv after 0-preprocess', required=True)
  parser.add_argument('-sd', '--singleday', help='create a single file with weekday average ', action='store_true')
  args = parser.parse_args()

  file_name = glob.glob(f'{args.dir}/*20*.csv')

  if args.singleday == False:

    df_collect_w = {}
    size_collect_w = {}

    df_collect_h = {}
    size_collect_h = {}

    for f in file_name:
      print(f'Processing file : {f}')
      hour_file = f.split('/')[-1].split('.')[0][-4:]
      date = f.split('/')[-1].split('.')[0]
      try:
        datet = datetime.strptime(date, '%y%m%d%H%M')
      except Exception as e:
        print(f'File {f} skipped for : {e}')
        continue

      df_w = pd.read_csv(f, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
      df_w.index = df_w.index.droplevel()

      if datet.weekday() < 5:
        if hour_file in df_collect_w:
          df_collect_w[hour_file] = df_collect_w[hour_file].add(df_w, fill_value=0)
          size_collect_w[hour_file] += 1
        else:
          df_collect_w[hour_file] = df_w
          size_collect_w[hour_file] = 1
      else:
        if hour_file in df_collect_h:
          df_collect_h[hour_file] = df_collect_h[hour_file].add(df_w, fill_value=0)
          size_collect_h[hour_file] += 1
        else:
          df_collect_h[hour_file] = df_w
          size_collect_h[hour_file] = 1


      df_tot_w = pd.DataFrame()
      for k,v in df_collect_w.items():
        v = v.div(size_collect_w[k]).astype(int)
        v = pd.concat({ k : v}, names=['hour'])
        df_tot_w = pd.concat([df_tot_w, v])
      df_tot_w.to_csv('od-average-weekdays.csv', sep=';',index=True)

      df_tot_h = pd.DataFrame()
      for k,v in df_collect_h.items():
        v = v.div(size_collect_h[k]).astype(int)
        v = pd.concat({ k : v}, names=['hour'])
        df_tot_h = pd.concat([df_tot_h, v])
      df_tot_h.to_csv('od-average-holidays.csv', sep=';',index=True)

  else:

    df_collect = {}
    size_collect = {}

    for i in np.arange(0,7):
      df_collect[i]={}
      size_collect[i]={}

    for f in file_name:
      print(f'Processing file : {f}')
      hour_file = os.path.split(f)[1].split('.')[0][-4:]
      date = os.path.split(f)[1].split('.')[0]

      try:
        datet = datetime.strptime(date, '%y%m%d%H%M')
      except Exception as e:
        print(f'File {f} skipped for : {e}')
        continue

      df_w = pd.read_csv(f, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
      df_w.index = df_w.index.droplevel()

      nd = datet.weekday()
      if hour_file in df_collect[nd]:
        df_collect[nd][hour_file] = df_collect[nd][hour_file].add(df_w, fill_value=0)
        size_collect[nd][hour_file] += 1
      else:
        df_collect[nd][hour_file] = df_w
        size_collect[nd][hour_file] = 1


    df_tot = pd.DataFrame()
    for i in np.arange(0,7):
      for k,v in df_collect[i].items():
        v = v.div(size_collect[i][k]).astype(int)
        v = pd.concat({ k : v}, names=['hour'])
        v = pd.concat({ i : v}, names=['n_day'])
        df_tot = pd.concat([df_tot, v])

    df_tot = df_tot.loc[(df_tot.sum(axis=1) != 0)]
    df_tot.to_csv(f'od-average-n-weekday.csv', sep=';',index=True)




