#! /usr/bin/env python3
#Using cartography and viasat Coorect


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
coilpolyfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers_cartodata.csv')

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-cf", "--coilsfile", help="coils table input csv", default='')
  parser.add_argument("-vf", "--viasatfile", help="viasat timed fluxes input csv", default='')
  parser.add_argument("-ua", "--uniqfileall", help="year of uniqs input")
  parser.add_argument("-bf", "--barfile", help="synthetic barriers input csv")
  parser.add_argument("-c", "--coils", help="list of coils id to filter plot output",  nargs='+', default=[])
  parser.add_argument("-p", "--polycid", help="list of poly cid to filter plot output",  nargs='+', default=[])
  args = parser.parse_args()

  outdir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'figure_compare')
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
    map_inv = {i:j for j,i in zip(coils_id, polycid_coil)}

  if len(args.polycid)!=0:
    poly_id = args.polycid
  else:
    poly_id = [37080, 18516, 86838, 105192, 104671, 37032, 277472, 21087, 51577, 105009, 123187, 191061, 123776, 186269, 402451, 117586, 48501, 36459]
  
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

  try:
    ##coils mean compare sum viasat
    if args.viasatfile and args.coilsfile:
      coil_viasat_dir = f'{outdir}/coil_viasat'
      if not os.path.exists(coil_viasat_dir):
        os.makedirs(coil_viasat_dir)
      viasat_df = pd.read_csv(args.viasatfile, sep=';')
      viasat_df.set_index(pd.to_datetime(viasat_df.time), inplace=True)
      startdate_sim = viasat_df.index[0]
      stopdate_sim = viasat_df.index[-1]

      viasat_df = viasat_df[(viasat_df.index >= startdate_sim ) & (viasat_df.index < stopdate_sim)]
      viasat_df = viasat_df[['total_fluxes','cid']]
      viasat_df = viasat_df[viasat_df.cid.isin(list(map_inv.keys()))]
      viasat_df['time_hour'] = viasat_df.index.time
      viasat_df = viasat_df.groupby(['time_hour','cid']).sum()
      viasat_df = viasat_df.unstack(level='cid')
      viasat_df.columns = viasat_df.columns.droplevel(level=0)
      coils_df = pd.read_csv(args.coilsfile, sep=';', index_col=0, parse_dates=True)
      coils_df = coils_df[[col for col in coils_df.columns for k in map_corrisp.keys() if str(k) in col ]]
      for k in map_corrisp.keys():
        if len(k) == 1 or len(k) == 2:
          coils_df = coils_df[[col for col in coils_df.columns if (col.startswith(k) and str(k + '_') in col) ]]
      local_timezone = pytz.timezone("Europe/Rome")
      coils_df['local_time'] = [i.astimezone(local_timezone) for i in coils_df.index.copy()]
      coils_df["local_time"]=coils_df["local_time"].dt.tz_localize(None)
      coils_df.set_index('local_time', inplace=True)
      coils_df = coils_df[ (coils_df.index >= startdate_sim) & (coils_df.index < stopdate_sim) ]
      coils_df = coils_df.interpolate(limit_direction='both')
      for k, v in map_corrisp.items():
        try:
          coils_df_w = coils_df[[col for col in coils_df.columns if str(k) in col]]
          coils_df_w[f'{v}'] = coils_df_w.copy().sum(axis=1)
          coils_df_w = coils_df_w[[f'{v}']]
          coils_df_w = coils_df_w.groupby(pd.Grouper(freq='H')).sum()
          coils_df_w['time_hour'] = coils_df_w.index.time
          coils_df_w = coils_df_w.groupby('time_hour').mean()
          viasat_df = viasat_df[[v]]
        except Exception as e:
          print('Exception: ', e)
        ## plot sum_viasat vs mean_coils
        w, h, d = 12, 7, 150
        fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
        tsd = [ t for t in range(len(coils_df_w.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ t.strftime('%H:%M:%S') for t in coils_df_w.index ]
        tsd_lbl = tsd_lbl[::lusd]
        ax.plot(tsd, coils_df_w, color='C0', label='MTS mean data')
        ax.set_ylabel('N MTS', color="C0")
        ax.set_xlabel('Hour (H:M:S)')
        ax.set_xticks(tsd)
        ax.set_xticklabels(tsd_lbl, rotation=45)
        ax.legend(loc='upper left')
        ax2=ax.twinx()
        ax2.plot(tsd, viasat_df, '--', color="C1", label='VIASAT sum data')
        ax2.set_ylabel('N viasat', color="C1")
        ax2.legend(loc='upper right')
        string_save_text = str(startdate_sim).split(' ')[0].replace('-','') +  str(stopdate_sim).split(' ')[0].replace('-','')
        string_title_text = 'From ' + str(startdate_sim).split(' ')[0] + ' to ' +  str(stopdate_sim).split(' ')[0]

        plt.title(f'Poly cid {v} (Coil {k})\n{string_title_text}')
        plt.tight_layout()
        outname = os.path.join(coil_viasat_dir, f'coil_viasat_{string_save_text}_cid{v}_coil_{k}.png')
        # fig.savefig(outname, dpi=150)
        # plt.show()
        plt.clf()
        plt.close()

    ## SIM uniq mean compare sum viasat
    elif args.viasatfile and args.uniqfileall:
      sim_viasat_dir = f'{outdir}/sim_viasat'
      if not os.path.exists(sim_viasat_dir):
        os.makedirs(sim_viasat_dir)

      try:
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
        for uniq_file in uniq_all:
          uniq_df = pd.read_csv(uniq_file, sep=';')
          uniq_df = uniq_df.groupby('poly_cid').sum()
          uniq_df = uniq_df.drop('poly_lid', axis=1)
          uniq_df.columns = pd.to_datetime(uniq_df.columns)
          uniq_df = uniq_df.loc[list(map_inv.keys())]
          uniq_df = uniq_df.T
          uniq_df.index.rename('datetime', inplace=True)
          # uniq_df.index = uniq_df.index.tz_localize(None).tz_convert('Europe/Rome')
          uniq_df['new_time'] = [i+timedelta(minutes=75) for i in uniq_df.index]
          uniq_df.set_index('new_time', inplace=True)
          uniq_df['hour'] = [int(str(i).split(' ')[-1].split(':')[0]) for i in uniq_df.index]
          datetime_list = [i for i in uniq_df.index.to_list() if "15:00" in str(i)]
          uniq_df = uniq_df.groupby(by='hour').sum()
          uniq_df['datetime'] = datetime_list
          uniq_df.set_index('datetime', inplace=True)
          uniq_df['time_index'] = uniq_df.index.time
          uniq_df.set_index('time_index', inplace=True)
          uniq_all_df=pd.concat([uniq_all_df, uniq_df], axis=1).fillna(0)
        uniq_df = uniq_all_df.groupby(by=uniq_all_df.columns, axis=1).mean()
      except:
        uniq_df = pd.DataFrame()

      viasat_df = pd.read_csv(args.viasatfile, sep=';')
      viasat_df.set_index(pd.to_datetime(viasat_df.time), inplace=True)
      startdate_sim = viasat_df.index[0]
      stopdate_sim = viasat_df.index[-1]
      viasat_df = viasat_df[(viasat_df.index >= startdate_sim ) & (viasat_df.index < stopdate_sim)]
      viasat_df = viasat_df[['total_fluxes','cid']]
      viasat_df = viasat_df[viasat_df.cid.isin(list(map_inv.keys()))]
      viasat_df['time_hour'] = viasat_df.index.time
      viasat_df = viasat_df.groupby(['time_hour','cid']).sum()
      viasat_df = viasat_df.unstack(level='cid')
      viasat_df.columns = viasat_df.columns.droplevel(level=0)
      for k in map_inv.keys():
        viasat_df_w = viasat_df[[k]]
        uniq_df_w = uniq_df[[k]]

        ## plot sum_viasat vs mean_coils
        w, h, d = 12, 7, 100
        fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
        tsd = [ t for t in range(len(viasat_df_w.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ t.strftime('%H:%M:%S') for t in viasat_df_w.index ]
        tsd_lbl = tsd_lbl[::lusd]
        ax.plot(tsd, uniq_df_w, color='C0', label='SIM mean data')
        ax.set_ylabel('N SIM', color="C0")
        ax.set_xlabel('Time (H:M:S)')
        ax.set_xticks(tsd)
        ax.set_xticklabels(tsd_lbl, rotation=45)
        ax.grid()
        ax.legend(loc='upper left')
        ax2=ax.twinx()
        ax2.plot(tsd, viasat_df_w, '--', color="C1", label='VIASAT sum data')
        ax2.set_ylabel('N viasat', color="C1")
        ax2.legend(loc='upper right')
        string_save_text = str(startdate_sim).split(' ')[0].replace('-','') +  str(stopdate_sim).split(' ')[0].replace('-','')
        string_title_text = 'From ' + str(startdate_sim).split(' ')[0] + ' to ' +  str(stopdate_sim).split(' ')[0]

        plt.title(f'Poly cid {k} \n{string_title_text}')
        plt.tight_layout()
        outname = os.path.join(sim_viasat_dir, f'sim_viasat_{string_save_text}_cid_{k}.png')
        fig.savefig(outname, dpi=150)
        print(f'Image saved in {outname}')
        plt.clf()
        plt.close()

    ## coil compare sim
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
        ## plot coil vs sim-barriers
        for num, coil in enumerate(list(args.coils)):
          try:
            poly = map_corrisp[coil]
            filter_col_bar =  [col for col in bar_df if col.startswith(coil)]
            filter_col_coils =  [col for col in coils_df if col.startswith(coil)]
            bar_df_small = bar_df[ filter_col_bar ]
            coils_df_small = coils_df [ filter_col_coils]
            bar_df_small.rename(columns={bar_df_small.columns[0]:'IN', bar_df_small.columns[1]:'OUT'}, inplace=True)
            coils_df_small.rename(columns={coils_df_small.columns[0]:'IN', coils_df_small.columns[1]:'OUT'}, inplace=True)
            w, h, d = 12, 7, 150
            fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d)
            height=(0, 1500)
            tsd = [ t for t in range(len(coils_df_small.index)) ]
            tusd = 1
            lusd = 1
            tsd_ticks = tsd[::tusd]
            tsd_lbl = [ t.strftime('%H:%M:%S') for t in coils_df_small.index ]
            tsd_lbl = tsd_lbl[::lusd]

            ax = axs[0]
            ax.plot(tsd, coils_df_small.IN, color='C0', label=f'MTS IN')
            ax.set_ylabel(f'N MTS (TOT : {str(round(coils_df_small.IN.sum()))}) ', color="C0")
            ax.set_xticks(tsd)
            ax.set_xticklabels(tsd_lbl, rotation=45)
            # ax.set_ylim(height)
            ax.grid()
            ax.legend(loc='upper left')
            ax2=ax.twinx()
            ax2.plot(tsd, bar_df_small.IN, '--', color="C1", label=f'SIM IN')
            ax2.set_ylabel(f'N sim (TOT : {str(round(bar_df_small.IN.sum()))})', color="C1")
            # ax2.set_ylim(height)
            ax2.legend(loc='upper right')


            ax = axs[1]
            ax.plot(tsd, coils_df_small.OUT, color='C0', label=f'MTS OUT')
            ax.set_ylabel(f'N MTS ( TOT : {str(round(coils_df_small.OUT.sum()))}) ', color="C0")
            ax.set_xlabel('Hour (H:M:S)')
            ax.set_xticks(tsd)
            ax.set_xticklabels(tsd_lbl, rotation=45)
            ax.grid()
            # ax.set_ylim(height)
            ax.legend(loc='upper left')

            ax2=ax.twinx()
            ax2.plot(tsd, bar_df_small.OUT, '--', color="C1", label=f'SIM OUT')
            ax2.set_ylabel(f'N sim (TOT : {str(round(bar_df_small.OUT.sum()))})', color="C1")
            # ax2.set_ylim(height)
            # ax2.grid()
            ax2.legend(loc='upper right')



            string_save_text = str(startdate_sim).split(' ')[0].replace('-','') +  str(stopdate_sim).split(' ')[0].replace('-','')
            string_title_text = 'From ' + str(startdate_sim).split(' ')[0] + ' to ' +  str(stopdate_sim).split(' ')[0]

            plt.suptitle(f'Poly cid {poly} (Coil {coil})\n{string_title_text}')
            plt.tight_layout()
            outname = os.path.join(coil_sim_dir, f'reggio/coil_sim_{string_save_text}_cid_{poly}_coil_{coil}.png')
            fig.savefig(outname, dpi=150)
            print(f'Image saved in {outname}')
            # plt.show()
            plt.clf()
            plt.close()
          except Exception as e:
            print(f'Exception: {e}')

      elif args.polycid:
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

            bar_df_small.IN = bar_df_small.IN
            bar_df_small.OUT = bar_df_small.OUT

            w, h, d = 12, 7, 100
            fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d)
            tsd = [ t for t in range(len(coils_df_small.index)) ]
            tusd = 1
            lusd = 1
            tsd_ticks = tsd[::tusd]
            tsd_lbl = [ t.strftime('%H:%M:%S') for t in coils_df_small.index ]
            tsd_lbl = tsd_lbl[::lusd]

            a,b = 0,1500
            ax = axs[0]
            ax.plot(tsd, coils_df_small.IN, color='C0', label=f'MTS IN')
            ax.set_ylabel(f'N MTS (TOT : {str(round(coils_df_small.IN.sum()))}) ', color="C0")
            ax.set_xticks(tsd)
            ax.set_xticklabels(tsd_lbl, rotation=45)
            ax.set_ylim(a,b)
            ax.legend(loc='upper left')
            ax2=ax.twinx()
            ax2.plot(tsd, bar_df_small.IN, '--', color="C1", label=f'SIM IN')
            ax2.set_ylabel(f'N sim (TOT : {str(round(bar_df_small.IN.sum()))})', color="C1")
            ax2.set_ylim(a,b)
            ax2.legend(loc='upper right')

            ax = axs[1]
            ax.plot(tsd, coils_df_small.OUT, color='C0', label=f'MTS OUT')
            ax.set_ylabel(f'N MTS (TOT : {str(round(coils_df_small.OUT.sum()))}) ', color="C0")
            ax.set_xlabel('Time (H:M:S)')
            ax.set_xticks(tsd)
            ax.set_xticklabels(tsd_lbl, rotation=45)
            ax.set_ylim(a,b)
            ax.legend(loc='upper left')
            ax2=ax.twinx()
            ax2.plot(tsd, bar_df_small.OUT, '--', color="C1", label=f'SIM OUT')
            ax2.set_ylabel(f'N sim (TOT : {str(round(bar_df_small.OUT.sum()))})', color="C1")
            ax2.set_ylim(a,b)
            ax2.legend(loc='upper right')

            string_save_text = str(startdate_sim).split(' ')[0].replace('-','') +  str(stopdate_sim).split(' ')[0].replace('-','')
            string_title_text = 'From ' + str(startdate_sim).split(' ')[0] + ' to ' +  str(stopdate_sim).split(' ')[0]

            plt.suptitle(f'Poly cid {poly} (Coil {coil})\n{string_title_text}')
            plt.tight_layout()
            outname = os.path.join(coil_sim_dir, f'coil_sim_{string_save_text}_cid_{poly}_coil_{coil}.png')

            fig.savefig(outname, dpi=150)
            # plt.show()
            plt.clf()
            plt.close()

          except Exception as e:
            print(print(f'Exception: {e}'))

    else:
      pass
  except Exception as e:
    print(f'exception: {e}')