#! /usr/bin/env python3

import argparse
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import haversine as hs
import numpy as np
import glob

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dir', help='preprocessed data directory', required=True)
args = parser.parse_args()

## make average hour matrices
hour_list = [str(item).zfill(4) for item in np.arange(0,2400,100)]
df_points = pd.DataFrame(columns=['id','name','points_O','points_D'])
for i in hour_list:
  print(i)
  datafiles = sorted(glob.glob(f'{args.dir}/*{i}.csv'))
  df = pd.DataFrame()
  for dataf in datafiles:
    data = pd.read_csv(dataf, sep=';', header=[0, 1], index_col=[0,1,2], parse_dates=True)
    df = df.append(data)

  df.columns = pd.MultiIndex.from_tuples([ (int(i), j) for i, j in df.columns ])
  df = df.reset_index(level=0, drop=True)
  df = df.reset_index()
  df = df.sort_values(by=['id_o'])

  df = df[[i for i in df.columns if i[1]!='N/A']]
  df = df.dropna(axis=0)

  df_tot = df.groupby(by=['id_o','name_o'], axis=0).sum()
  df_tot = df_tot.reset_index(level=[0,1])

  df_w_O = pd.DataFrame()
  df_w_O['id']= df_tot['id_o']
  df_w_O['name']= df_tot['name_o']
  df_w_O['points_O'] = df_tot[df_tot.columns[1:]].sum(axis=1).to_list()

  df_w_D = pd.DataFrame()
  df_w_D['id'] = df_tot.columns.get_level_values(0).to_list()[2:]
  df_w_D['name'] = df_tot.columns.get_level_values(1).to_list()[2:]
  df_w_D['points_D'] = df_tot.sum().to_list()[2:]

  df_w = pd.merge(df_w_O, df_w_D, on=['name','id'], how='outer')
  df_points = df_points.append(df_w)

df_points_mean = df_points.groupby(['id','name']).mean()
df_points_mean = df_points_mean.fillna(0)
df_points_mean['mean_points'] = ((df_points_mean['points_D']+df_points_mean['points_O'])/2.)
df_points_mean = df_points_mean.sort_values(by='mean_points', ascending=False)
df_points_mean=df_points_mean.astype({'points_O':int, 'points_D':int,'mean_points':int})
df_points_mean = df_points_mean[df_points_mean.mean_points>0.0]
df_points_mean.to_csv(args.dir+'/city_activity.csv', sep=';', index=True)
