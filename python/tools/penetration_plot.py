#! /usr/bin/env python3

import os
import sys
import glob
import json
import pytz
import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
import scipy.stats as st
import matplotlib.pyplot as plt
from datetime import timedelta
from datetime import datetime

cartofile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-carto.geojson')
coilpolyfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'od_cartodata.csv')

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-uf", "--uniqfile", help="synthetic uniq input csv")
  parser.add_argument("-bf", "--barfile", help="synthetic barrier input csv")
  parser.add_argument("-ua", "--uniqfileall", help="year of uniqs input")
  parser.add_argument("-cf", "--coilsfile", help="coils table input csv", default='')
  parser.add_argument("-vf", "--viasatfile", help="viasat timed fluxes input csv", default='')
  parser.add_argument("-c", "--coils", help="list of coils id to filter plot output",  nargs='+', default=[])
  parser.add_argument("-p", "--polycid", help="list of poly cid to filter plot output",  nargs='+', default=[])
  args = parser.parse_args()

  outdir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'penetration')
  if not os.path.exists(outdir):
    os.makedirs(outdir)

  carto = gpd.read_file(cartofile)
  carto = carto.set_index('poly_cid')

  coilpm = pd.read_csv(coilpolyfile, sep=';', encoding='ISO-8859-1').sort_values(by='tag')
  coilpm = coilpm.set_index('tag')

  if len(args.coils)!=0:
    coils_id = args.coils
    polylid_coil = [coilpm.loc[int(i), 'poly_lid'] for i in coils_id]
    polycid_coil = [carto[carto.poly_lid == i].index.values[0] for i in polylid_coil]
    map_corrisp = {i:j for i,j in zip(coils_id, polycid_coil)}

  if len(args.polycid)!=0:
    poly_id = args.polycid
    poly_lid = [carto.loc[int(i), 'poly_lid'] for i in poly_id]
    polylid_coil=[]
    for i in poly_lid:
      try:
        val = list(coilpm[coilpm.poly_lid == i].index)[0]
      except:
        val = '-1'
      polylid_coil.append(val)
    map_corrisp = {str(i):int(j) for i,j in zip(polylid_coil, poly_id)}
    map_inv = {int(j):str(i) for i,j in zip(polylid_coil, poly_id)}

  if args.viasatfile and not args.coilsfile:
    try:
      if not args.uniqfileall:
        uniq_df = pd.read_csv(args.uniqfile,sep=';')
        uniq_df = uniq_df.groupby('poly_cid').sum()
        uniq_df = uniq_df.drop('poly_lid', axis=1)
        startdate_sim = uniq_df.columns[1]
        stopdate_sim = uniq_df.columns[-1]
        uniq_df.columns = pd.to_datetime(uniq_df.columns)
        uniq_df = uniq_df.loc[list(map_inv.keys())]
        uniq_df = uniq_df.T
        uniq_df.index.rename('datetime', inplace=True)
        uniq_df['new_time'] = [i+timedelta(minutes=15) for i in uniq_df.index]
        uniq_df.set_index('new_time', inplace=True)
        uniq_df['hour'] = [int(str(i).split(' ')[-1].split(':')[0]) for i in uniq_df.index]
        datetime_list = [i for i in uniq_df.index.to_list() if "15:00" in str(i)]
        uniq_df = uniq_df.groupby(by='hour').sum()
        uniq_df['datetime'] = datetime_list
        uniq_df.set_index('datetime', inplace=True)

      else:
        if args.uniqfileall == '2020':
          uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2020', 'uniq')
          startdate_sim = pd.to_datetime('2020-02-10')
          stopdate_sim = pd.to_datetime('2020-02-17')
        elif args.uniqfileall == '2021':
          uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2021', 'uniq')
          startdate_sim = pd.to_datetime('2021-06-28')
          stopdate_sim = pd.to_datetime('2021-07-04')

        uniq_all = sorted(glob.glob(uniq_path + '/*.csv.corrected'))
        uniq_all_df = pd.DataFrame()
        counter = 0
        for uniq_file in uniq_all:
          uniq_df = pd.read_csv(uniq_file, sep=';')
          uniq_df = uniq_df.groupby('poly_cid').sum()
          uniq_df = uniq_df.drop('poly_lid', axis=1)
          uniq_df.columns = pd.to_datetime(uniq_df.columns)
          uniq_df = uniq_df.loc[list(map_inv.keys())]
          uniq_df = uniq_df.T
          uniq_df.index.rename('datetime', inplace=True)
          uniq_df['new_time'] = [i+timedelta(minutes=15) for i in uniq_df.index]
          uniq_df.set_index('new_time', inplace=True)
          uniq_df['hour'] = [int(str(i).split(' ')[-1].split(':')[0]) for i in uniq_df.index]
          datetime_list = [i for i in uniq_df.index.to_list() if "15:00" in str(i)]
          uniq_df = uniq_df.groupby(by='hour').sum()
          uniq_df['datetime'] = datetime_list
          uniq_df.set_index('datetime', inplace=True)
          uniq_df['time_index'] = uniq_df.index.time
          uniq_df.set_index('time_index', inplace=True)
          uniq_all_df=pd.concat([uniq_all_df, uniq_df], axis=1).fillna(0)
          counter = counter + 1
        uniq_df = uniq_all_df.groupby(by=uniq_all_df.columns, axis=1).mean()
        print(startdate_sim, stopdate_sim)
    except:
      print('No uniq given')
      uniq_df = pd.DataFrame()

    viasat_df = pd.read_csv(args.viasatfile, sep=';')
    viasat_df.set_index(pd.to_datetime(viasat_df.time), inplace=True)

    if not args.uniqfileall:
      viasat_df = viasat_df[(viasat_df.index >= startdate_sim ) & (viasat_df.index < stopdate_sim)]
      viasat_df = viasat_df[['total_fluxes','cid']]
      viasat_df = viasat_df[viasat_df.cid.isin(list(map_inv.keys()))]
    else:
      viasat_df = viasat_df[['total_fluxes','cid']]
      viasat_df = viasat_df[viasat_df.cid.isin(list(map_inv.keys()))]
      viasat_df['time_index'] = viasat_df.index.time
      viasat_df = viasat_df.groupby(['time_index','cid']).mean()
      # viasat_df = viasat_df.groupby(['time_index','cid']).sum()
      viasat_df = viasat_df.unstack(level='cid')
      viasat_df.columns = viasat_df.columns.droplevel(level=0)

    stringname = str(startdate_sim).split(' ')[0].replace('-','')
    penetration_list = []
    for k,v in map_inv.items():
      # print('poly: ', k)
      uniq_df_w = uniq_df[k]
      if not args.uniqfileall:
        viasat_df_w = viasat_df[viasat_df.cid==k]
        viasat_sum = viasat_df_w.total_fluxes.to_numpy().sum()
      else:
        viasat_df_w = viasat_df[k]
        viasat_sum = viasat_df_w.to_numpy().sum()

      unique_sum = uniq_df_w.to_numpy().sum()
      penetration = viasat_sum / unique_sum
      penetration = penetration * 100
      penetration_list.append((k,penetration))
    penetration_df = pd.DataFrame(penetration_list, columns=['poly_cid','penetration'])
    penetration_df.set_index('poly_cid', inplace=True)

    w, h, d = 12, 7, 100
    fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
    tsd = [ p for p in range(len(penetration_df.index)) ]

    tusd = 1
    lusd = 1
    tsd_ticks = tsd[::tusd]
    tsd_lbl = [ str(p) for p in penetration_df.index ]
    tsd_lbl = tsd_lbl[::lusd]
    width = 0.8
    bar_1 = ax.bar(tsd, penetration_df.penetration, width=width)
    for rect in bar_1:
      height = rect.get_height()
      ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
    ax.set_xticks(tsd_ticks)
    ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
    ax.set_ylabel('Penetration [%]')
    ax.set_xlabel('Poly CID')
    ax.set_ylim(0, 5)
    if not args.uniqfileall:
      plt.title(f'Statistic penetration {str(startdate_sim).split(" ")[0]}\n viasat/sim')
      outname = os.path.join(outdir, f'penetrazione_statistica_{stringname}.png')
    else:
      plt.title(f'Statistic penetration from {str(startdate_sim).split(" ")[0]} to {str(stopdate_sim).split(" ")[0]}\n viasat/sim')
      outname = os.path.join(outdir, f'penetrazione_statistica_{str(startdate_sim).split(" ")[0].replace("-","")}_{str(stopdate_sim).split(" ")[0].replace("-","")}.png')
    fig.savefig(outname, dpi=150)
    print(f'Image saved in {outname}')
    plt.clf()
    plt.close()

  elif args.coilsfile and args.barfile:
    coil_sim_dir = f'{outdir}/coil_sim'
    if not os.path.exists(coil_sim_dir):
      os.makedirs(coil_sim_dir)
    try:
      bar_df = pd.read_csv(args.barfile, delimiter=';')
      bar_df.index = pd.to_datetime(bar_df.datetime)
      startdate_sim = bar_df.index[0]
      stopdate_sim = bar_df.index[-1]
      print(startdate_sim, stopdate_sim)
      bar_df = bar_df.drop(['datetime','timestamp'], axis=1)
      bar_df = bar_df[[col for col in bar_df.columns for k in map_corrisp.keys() if str(k) in col ]]
      bar_df['new_time'] = [i + timedelta(minutes=15) for i in bar_df.index]
      bar_df.set_index('new_time', inplace=True)
    except:
      bar_df = pd.DataFrame()

    try:
      coils_df = pd.read_csv(args.coilsfile, sep=';', index_col=0, parse_dates=True)
      coils_df = coils_df.interpolate()
      coils_df = coils_df[[col for col in coils_df.columns for k in map_corrisp.keys() if str(k) in col ]]
      local_timezone = pytz.timezone("Europe/Rome")
      coils_df['local_time'] = [i.astimezone(local_timezone) for i in coils_df.index.copy()]
      coils_df["local_time"]=coils_df["local_time"].dt.tz_localize(None)
      coils_df.set_index('local_time', inplace=True)
      coils_df = coils_df[ (coils_df.index >= startdate_sim) & (coils_df.index < stopdate_sim) ]
      coils_df['new_time'] = [i + timedelta(minutes=15) for i in coils_df.index]
      coils_df.set_index('new_time', inplace=True)
      coils_df = coils_df.groupby([pd.Grouper(freq = '1H')]).sum()
    except Exception as e:
      print(f'Exception: {e}')
      coils_df = pd.DataFrame()

    if args.coils:
      penetration_list = []
      for num, coil in enumerate(list(args.coils)):
        try:
          poly = map_corrisp[coil]
          filter_col_bar =  [col for col in bar_df if col.startswith(coil)]
          filter_col_coils =  [col for col in coils_df if col.startswith(coil)]
          bar_df_small = bar_df[ filter_col_bar ]
          coils_df_small = coils_df [ filter_col_coils]
          bar_df_small.rename(columns={bar_df_small.columns[0]:'IN', bar_df_small.columns[1]:'OUT'}, inplace=True)
          coils_df_small.rename(columns={coils_df_small.columns[0]:'IN', coils_df_small.columns[1]:'OUT'}, inplace=True)

          bar_df_small['summed'] = bar_df_small.sum(axis=1)
          coils_df_small['summed'] = coils_df_small.sum(axis=1)

          sum_bar_summed = bar_df_small.summed.to_numpy().sum()
          sum_coil_summed = coils_df_small.summed.to_numpy().sum()
          penetration_summed = (sum_coil_summed / sum_bar_summed)
          penetration_list.append((poly, penetration_summed))

        except Exception as e:
          print(print(f'Exception: {e}'))

      penetration_df = pd.DataFrame(penetration_list, columns=['poly_cid','penetration'])
      penetration_df.set_index('poly_cid', inplace=True)

      w, h, d = 12, 7, 100
      fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
      tsd = [ p for p in range(len(penetration_df.index)) ]

      tusd = 1
      lusd = 1
      tsd_ticks = tsd[::tusd]
      tsd_lbl = [ str(p) for p in penetration_df.index ]
      tsd_lbl = tsd_lbl[::lusd]
      width = 0.8
      bar_1 = ax.bar(tsd, penetration_df.penetration, width=width)
      for rect in bar_1:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
      ax.set_xticks(tsd_ticks)
      ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
      ax.set_ylabel('Penetration [%]')
      ax.set_xlabel('Poly CID')
      ax.set_ylim(0, 10)
      plt.title(f'Ratio from {str(startdate_sim).split(" ")[0]} to {str(stopdate_sim).split(" ")[0]}\n coil/sim')
      outname = os.path.join(coil_sim_dir, f'ratio_{str(startdate_sim).split(" ")[0].replace("-","")}_{str(stopdate_sim).split(" ")[0].replace("-","")}.png')
      fig.savefig(outname, dpi=150)
      print(f'Image saved in {outname}')
      # plt.show()
      plt.clf()
      plt.close()

    elif args.polycid:
      penetration_list = []
      for num, poly in enumerate(list(args.polycid)):
        try:
          poly = int(poly)
          coil = map_inv[poly]
          filter_col_bar =  [col for col in bar_df if col.startswith(coil)]
          filter_col_coils =  [col for col in coils_df if col.startswith(coil)]
          bar_df_small = bar_df[ filter_col_bar ]
          coils_df_small = coils_df [ filter_col_coils]
          bar_df_small.rename(columns={bar_df_small.columns[0]:'IN', bar_df_small.columns[1]:'OUT'}, inplace=True)
          coils_df_small.rename(columns={coils_df_small.columns[0]:'IN', coils_df_small.columns[1]:'OUT'}, inplace=True)

          bar_df_small['summed'] = bar_df_small.sum(axis=1)
          coils_df_small['summed'] = coils_df_small.sum(axis=1)

          sum_bar_summed = bar_df_small.summed.to_numpy().sum()
          sum_coil_summed = coils_df_small.summed.to_numpy().sum()
          penetration_summed = (sum_coil_summed / sum_bar_summed)
          penetration_list.append((poly, penetration_summed))

        except Exception as e:
          print(print(f'Exception: {e}'))

      penetration_df = pd.DataFrame(penetration_list, columns=['poly_cid','penetration'])
      penetration_df.set_index('poly_cid', inplace=True)

      w, h, d = 12, 7, 100
      fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
      tsd = [ p for p in range(len(penetration_df.index)) ]

      tusd = 1
      lusd = 1
      tsd_ticks = tsd[::tusd]
      tsd_lbl = [ str(p) for p in penetration_df.index ]
      tsd_lbl = tsd_lbl[::lusd]
      width = 0.8
      bar_1 = ax.bar(tsd, penetration_df.penetration, width=width)
      for rect in bar_1:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
      ax.set_xticks(tsd_ticks)
      ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
      ax.set_ylabel('Penetration [%]')
      ax.set_xlabel('Poly CID')
      ax.set_ylim(0, 10)
      plt.title(f'Ratio from {str(startdate_sim).split(" ")[0]} to {str(stopdate_sim).split(" ")[0]}\n coil/sim')
      outname = os.path.join(outdir, f'ratio_{str(startdate_sim).split(" ")[0].replace("-","")}_{str(stopdate_sim).split(" ")[0].replace("-","")}.png')
      fig.savefig(outname, dpi=150)
      # plt.show()
      plt.clf()
      plt.close()