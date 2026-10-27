#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import argparse
import glob
import json
import os
import re
import sys
import pytz
from datetime import datetime, timedelta
import time

class config():

  def __init__(self, config):
    self.short_fmt = '%y%m%d_%H%M%S'
    self.date_fmt = '%Y-%m-%d %H:%M:%S'
    self.tz_rome = pytz.timezone('Europe/Rome')
    self.config = config
    self.rates_dt = 900
    self.date_format = '%Y-%m-%d %H:%M:%S'
    self.creation_dt = 30

  def schedule_od(self):
    config = self.config
    ### config variables
    sim_times = config['sim_times']
    num_city = config['num_city']
    coilscsv = config['coils_table_file']

    without_rnd = config['random']

    try:
      filter_coils_plot = config['filter_coils_plot']
    except:
      filter_coils_plot = []
    tag = 'od'

    try:
      augmentation = config['augmentation']
    except:
      augmentation = {}


    ### load sim template
    template_json = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'templates', 'check_template.json')
    with open(template_json) as tin:
      simtemplate = json.load(tin)

    ### read coils data
    dfcoils = pd.read_csv(coilscsv, sep=';', index_col=0, parse_dates=True)
    dfcoils = dfcoils.interpolate()

    ### select City of interest
    activity_file = os.path.join(config['od_average_dir'], 'city_activity.csv')
    df_city = pd.read_csv(activity_file, sep=';')
    df_city = df_city.iloc[:int(num_city)]
    act_id = [str(item).zfill(9) for item in df_city['id']]
    df_city['id'] = act_id
    # print(df_city)

    ### load City geodata
    filecoords = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'italy_com.csv')
    df_coord = pd.read_csv(filecoords, sep=';', dtype={'UID':'str'})
    df_coord['id'] = df_coord['UID']
    df_city = pd.merge(df_city, df_coord[['id', 'LAT', 'LON']], how='left',on='id')
    df_city = df_city.set_index('id', drop=False)
    # print(df_city.columns)
    # print(df_city)

    schedule=[]
    for start_date, stop_date in sim_times:
      ### convert datetime format to file name format
      start = pd.to_datetime(start_date + 'CET', format=self.date_fmt + '%Z')
      stop = pd.to_datetime(stop_date + 'CET', format=self.date_fmt + '%Z')
      timetag = f'{start.strftime(self.short_fmt)}_{stop.strftime(self.short_fmt)}'
      str_date = str(start.year)[2:]+str(start.month).zfill(2)+str(start.day).zfill(2) # ma dai...
      hour_list = [str(item).zfill(2)+'00' for item in np.arange(int(start.hour)+1, int(stop.hour)+1)]
      file_name = [str_date+s+'.csv' for s in hour_list]
      if len(file_name) == 0:
        raise Exception(f'No rpc-rpc file found, adjust sim timerange')

      # select coils data for synthvscam
      dfb = dfcoils[ (dfcoils.index >= start) & (dfcoils.index < stop) ]

      df = pd.DataFrame()
      df_dest = pd.DataFrame()
      df_src = pd.DataFrame()
      df_rnd = pd.DataFrame()
      for f in file_name:
        #print(f'Processing file : {f}')

        fpath = os.path.join(config['dir_table'], f)
        df_w = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
        df_w.index = pd.MultiIndex.from_tuples([ (t, f'{i:09d}', n) for t,i,n in df_w.index ], names=['time', 'id_o', 'name_o']) # hardfix for pandas>1.0.1

        # hacking timetable with augmentation factor
        for city,val_aug in augmentation.items():
          # increase traffic towards D
          df_w.loc[(slice(None),slice(None),city),:] *=val_aug
          # increase traffic from O
          df_w.iloc[:, df_w.columns.get_level_values(1)==city] = df_w.iloc[:, df_w.columns.get_level_values(1)==city].multiply(val_aug)

        ### rnd-dest curve
        df_wd = df_w.loc[~df_w.index.isin(act_id, level=1)]
        date = '20'+f.split('.')[0]
        ts = datetime.strptime(date, '%Y%m%d%H%M')
        df_wd = df_wd[act_id].sum().reset_index(name=ts)
        if len(df_dest)==0:
          df_dest = df_wd
        else:
          df_dest = pd.merge(df_dest, df_wd, on=['name_d','id_d'])
        #print(df_dest)

        ### source-rnd curve
        df_ws = df_w.loc[df_w.index.isin(act_id, level=1)]
        date = '20'+f.split('.')[0]
        ts = datetime.strptime(date, '%Y%m%d%H%M')
        df_ws = df_ws.sort_index(axis=1).drop(columns=act_id).sum(axis=1).reset_index(name=ts)
        df_ws = df_ws.drop(columns='time')
        if len(df_src)==0:
          df_src = df_ws
        else:
          df_src = pd.merge(df_src, df_ws, on=['name_o','id_o'])
        #print(df_src)

        ### rnd-rnd curve
        df_wrnd = df_w.loc[~df_w.index.isin(act_id, level=1)]
        num_rnd = df_wrnd.sort_index(axis=1).drop(act_id,axis=1).sum(axis=1).sum()
        date = '20'+f.split('.')[0]
        ts = datetime.strptime(date, '%Y%m%d%H%M')
        df_rnd[ts] = [num_rnd]

        ### source-dest curve
        df_w = df_w.loc[df_w.index.isin(act_id, level=1)]
        df_w = df_w[act_id]
        df_w = df_w.reset_index(level=0, drop=False)
        df = df.append(df_w)

      # print(df_src)
      # print(df_dest)
      # print(df_rnd)
      # print(df)

      rates_per_day = 24 * 60 * 60 // self.rates_dt
      mid_start = datetime.strptime(start.strftime('%Y-%m-%d 00:00:00'), self.date_format)
      ttrates = { t : 0 for t in [ mid_start + i* timedelta(seconds=self.rates_dt) for i in range(rates_per_day) ] }
      sources = {}

      tot_rnd_dest = df_dest[df_dest.columns[2:]].sum(axis=1).sum()
      tot_src_rnd  = df_src[df_src.columns[2:]].sum(axis=1).sum()
      tot_rnd_rnd  = df_rnd.sum(axis=1).iloc[0]
      tot_src_dest = df[df.columns[1:]].sum(axis=1).sum()
      tot_pawn = tot_rnd_dest + tot_src_rnd + tot_rnd_rnd + tot_src_dest

      print(f'city-city :{(tot_src_dest/tot_pawn*100):.2f} %')
      print(f'city-rnd  :{(tot_src_rnd/tot_pawn*100):.2f} %')
      print(f'rnd-city  :{(tot_rnd_dest/tot_pawn*100):.2f} %')
      print(f'rnd-rnd   :{(tot_rnd_rnd/tot_pawn*100):.2f} %')

      if without_rnd == False:
        ### rnd-dest curve
        for row in df_dest.iterrows():
          uid = row[1][0] # com istat code RRRPPPCCC
          rates = { t : v
            for t,v in zip((df_dest.columns[2:]- timedelta(hours=1)).to_list(), row[1][2:].to_list())
          }
          tt = ttrates.copy()
          tt.update(rates)
          keys = sorted(tt.keys())
          last_value = list(rates.keys())[-1]+timedelta(hours=1)
          keys = [k for k in keys if k<last_value]
          for i in np.arange(1, len(keys)):
            if tt[keys[i]]==0:
              tt[keys[i]] = tt[keys[i-1]]
          name_source = row[1][1]
          sources.update({
            name_source+'_dest_OUT':{
              'creation_dt' : self.creation_dt,
              'creation_rate' : [ int(v) for v in tt.values() ],
              'dest_location':{
                'lat' : df_city.loc[uid, 'LAT'],
                'lon' : df_city.loc[uid, 'LON'],
              },
              'pawns': {
                'rnd_dest' : {
                  'alpha_we'       : 1.0,
                  'beta_bp_miss'   : 1.0,
                  'alpha_speed'    : 0.0,
                  'TTB'            : 7200,
                  'vmin_mps'       : 15,
                  'vmax_mps'       : 25,
                  'start_node_lid' : -1,
                  'cherry_pick'    : 'medium',
                }
              }
            }
          })

        ### src-rnd curve
        for row in df_src.iterrows():
          uid = row[1][0]
          rates = { t : v
            for t,v in zip((df_src.columns[2:]- timedelta(hours=1)).to_list(), row[1][2:].to_list())
          }
          tt = ttrates.copy()
          tt.update(rates)
          keys = sorted(tt.keys())
          last_value = list(rates.keys())[-1]+timedelta(hours=1)
          keys = [k for k in keys if k<last_value]
          for i in np.arange(1, len(keys)):
            if tt[keys[i]]==0:
              tt[keys[i]] = tt[keys[i-1]]
          name_source = row[1][1]
          sources.update({
            name_source+'_src_IN':{
              'creation_dt' : self.creation_dt,
              'creation_rate' : [ int(v) for v in tt.values() ],
              'source_location':{
                'lat' : df_city.loc[uid, 'LAT'],
                'lon' : df_city.loc[uid, 'LON'],
              },
              'pawns': {
                'src_rnd' : {
                  'alpha_we'     : 1.0,
                  'beta_bp_miss' : 1.0,
                  'alpha_speed'  : 0.0,
                  'TTB'          : 7200,
                  'vmin_mps'     : 15,
                  'vmax_mps'     : 25,
                  'dest'         : -1,
                  'cherry_pick'    : 'medium',
                }
              }
            }
          })

        ### rnd-rnd curve
        rates = { t : v
          for t,v in zip((df_rnd.columns - timedelta(hours=1)).to_list(), df_rnd.iloc[0].to_list())
        }
        tt = ttrates.copy()
        tt.update(rates)
        keys = sorted(tt.keys())
        last_value = list(rates.keys())[-1]+timedelta(hours=1)
        keys = [k for k in keys if k<last_value]
        for i in np.arange(1, len(keys)):
          if tt[keys[i]]==0:
            tt[keys[i]] = tt[keys[i-1]]
        sources.update({
          'LOCALS':{
            'creation_dt' : self.creation_dt,
            'creation_rate' : [ int(v) for v in tt.values() ],
            'pawns': {
              'rnd_rnd' : {
                'alpha_we'       : 1.0,
                'beta_bp_miss'   : 1.0,
                'alpha_speed'    : 0.0,
                'vmin_mps'       : 15,
                'vmax_mps'       : 25,
                'TTB'            : 7200,
                'start_node_lid' : -1,
                'dest'           : -1,
                'cherry_pick'    : 'medium',
              }
            }
          }
        })


      ### src-dest curve
      dfgrp = df.groupby(df.index)
      for k,dfk in dfgrp:
        #print(k, dfk)
        source_lat = df_city.loc[k[0], 'LAT']
        source_lon = df_city.loc[k[0], 'LON']
        for j in dfk.columns[1:]:
          if dfk[j].sum()>0.0 and int(j[0])!=int(k[0]): ##la seconda condizone: mobilità locale
            dest_lat = df_city.loc[j[0], 'LAT']
            dest_lon = df_city.loc[j[0], 'LON']
            name_source = k[1].replace(' ','')+'_'+j[1].replace(' ','')
            rates = { t : v
              for t,v in zip((dfk['time'] - timedelta(hours=1)).to_list(), dfk[j].values)
            }
            tt = ttrates.copy()
            tt.update(rates)
            keys = sorted(tt.keys())
            last_value = list(rates.keys())[-1]+timedelta(hours=1)
            keys = [k for k in keys if k<last_value]
            for i in np.arange(1, len(keys)):
              if tt[keys[i]]==0:
                tt[keys[i]] = tt[keys[i-1]]
            sources.update({
              name_source+'_IN' : {
                'creation_dt' : self.creation_dt,
                'creation_rate' : [ int(v) for v in tt.values() ],
                'source_location' : {
                  'lat' : source_lat,
                  'lon' : source_lon
                  },
                'dest_location':{
                  'lat' : dest_lat,
                  'lon' : dest_lon,
                },
                'pawns': {
                  'scr_dest' : {
                    'alpha_we'     : 1.0,
                    'beta_bp_miss' : 0.0,
                    'alpha_speed'  : 0.0,
                    'vmin_mps'     : 15,
                    'vmax_mps'     : 25
                  }
                }
              }
            })

      #print(f'Sources:     {len(sources)}')
      simc = { k : v for k, v in simtemplate.items() }
      simc['state_basename'] = f'{tag}_{timetag}/{tag}'
      simc['start_date'] = start_date
      simc['stop_date'] = stop_date
      simc['sources'] = sources
      simc['enable_influxgrid'] = True
      simc['state_grid_cell_m'] = 5000
      simc['coils_table_file'] = coilscsv
      simc['cherry_pick_mode'] = {'medium':5.0} # in km
      simc['file_score_pop'] = file_ace_score
      #simc['enable_uniq_poly'] = True;

      # parasitic parameters, unrelated to simulation
      simc['filter_coils_plot'] = filter_coils_plot
      simc['timetag'] = timetag
      simc['tag'] = tag

      schedule.append([dfb, simc])
      print(f'Sim config created for {start_date} - {stop_date} with schedule_od')

    return schedule

  def schedule_od_average(self):
    ex_start_time = time.time()
    ### config variables
    config = self.config
    sim_times = config['sim_times']
    num_city = config['num_city']
    coilscsv = config['coils_table_file']

    without_rnd = config['random']
    config.pop('random',None)

    try:
      filter_coils_plot = config['filter_coils_plot']
    except:
      filter_coils_plot = []
    tag = 'od'

    try:
      augmentation = config['augmentation']
    except:
      augmentation = {}

    try:
      augmentation_prov = config['augmentation_prov']
    except:
      augmentation_prov = {}

    ### load sim template
    template_json = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'templates', 'check_template.json')
    with open(template_json) as tin:
      simtemplate = json.load(tin)

    ### load ace score data
    file_ace_score = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'ace_score.csv')

    ### read coils data
    dfcoils = pd.read_csv(coilscsv, sep=';', index_col=0, parse_dates=True)
    dfcoils = dfcoils.interpolate()

    ### select City of interest
    activity_file = os.path.join(config['od_average_dir'], 'city_activity.csv')
    df_city = pd.read_csv(activity_file, sep=';')
    df_city = df_city.iloc[:int(num_city)]
    act_id = [str(item).zfill(9) for item in df_city['id']]
    df_city['id'] = act_id
    # print(df_city)

    ### select Prov of interest
    activity_prov_file = os.path.join(config['od_average_dir'], 'prov_activity.csv')
    df_prov = pd.read_csv(activity_prov_file, sep=';')
    act_prov_id = [str(item).zfill(9) for item in df_prov['id']]
    df_prov['id'] = [ap[3:] for ap in act_prov_id]

    ### load City geodata
    filecoords = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'italy_com.csv')
    df_coord = pd.read_csv(filecoords, sep=';', dtype={'UID':'str'})
    df_coord['id'] = df_coord['UID']
    df_city = pd.merge(df_city, df_coord[['id', 'LAT', 'LON']], how='left',on='id')
    df_city = df_city.set_index('id', drop=False)
    # print(df_city.columns)
    # print(df_city)
    schedule=[]
    for start_date, stop_date in sim_times:
      ### convert datetime format to file name format
      start = pd.to_datetime(start_date + 'CET', format=self.date_fmt + '%Z')
      stop = pd.to_datetime(stop_date + 'CET', format=self.date_fmt + '%Z')
      timetag = f'{start.strftime(self.short_fmt)}_{stop.strftime(self.short_fmt)}'
      str_date = str(start.year)[2:]+str(start.month).zfill(2)+str(start.day).zfill(2) # ma dai...
      hour_list = [int(str(item).zfill(2)+'00') for item in np.arange(int(start.hour)+1, int(stop.hour)+1)]

      #### RPC - RPC sources ###
      ## read average file
      if start.weekday()<5:
        fpath = os.path.join(config['od_average_dir'], 'od-average-weekdays.csv')
        df_w = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
      else:
        fpath = os.path.join(config['od_average_dir'], 'od-average-holidays.csv')
        df_w = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)

      # select coils data for synthvscam
      if 'wday_n' in dfcoils.columns:
        wday = start.strftime('%w')
        dfcoils=dfcoils[dfcoils.wday_n==int(wday)]
        hour_list_wday = dfcoils['time'].to_list()
        dfcoils = dfcoils.drop(['time','wday_n'], axis=1)
        day_start = datetime.strptime(f'{start.year}-{start.month}-{start.day} 00:00:00', self.date_fmt)

        datetime_list = [day_start.replace(hour=int(t.split(':')[0]), minute=int(t.split(':')[1]), second=0) for t in hour_list_wday]
        dfcoils.index = [pd.to_datetime(str(i) + 'GMT', format=self.date_fmt + '%Z') for i in datetime_list  ]
        dfcoils.index.name = 'datetime'

      dfb = dfcoils[ (dfcoils.index >= start) & (dfcoils.index < stop) ]

      df_w = df_w.loc[df_w.index.isin(hour_list, level=0)]
      # hacking timetable with augmentation factor
      augmented = False
      for city,val_aug in augmentation.items():
        o_city = city.split('_')[0]
        d_city = city.split('_')[1]
        if (df_w.loc[(slice(None),slice(None),o_city),df_w.columns.get_level_values(1)==d_city].sum().values[0] > 50):
          df_w.loc[(slice(None),slice(None),o_city),df_w.columns.get_level_values(1)==d_city] *= val_aug
          augmented = True
      if augmented==False and len(augmentation)!=0:
        return ''

      ### rnd-dest curve
      act_id_int = [int(i) for i in act_id]
      df_wd = df_w.loc[~df_w.index.isin(act_id_int, level=1)]
      df_wd = df_wd[act_id]
      df_dest = df_wd.groupby(level='hour').sum()

      ### source-rnd curve
      df_ws = df_w.loc[df_w.index.isin(act_id_int, level=1)]
      df_src = df_ws.sort_index(axis=1).drop(columns=act_id).sum(axis=1)
      #print(df_src)

      ### rnd-rnd curve
      df_wrnd = df_w.loc[~df_w.index.isin(act_id_int, level=1)]
      df_rnd = df_wrnd.sort_index(axis=1).drop(act_id,axis=1).sum(axis=1).groupby(level='hour').sum()

      ### source-dest curve
      df_w = df_w.loc[df_w.index.isin(act_id_int, level=1)]
      df = df_w[act_id]

      #### RP - RP sources ###
      ## read average prov file
      if start.weekday()<5:
        fpath = os.path.join(config['od_average_dir'], 'od-prov-average-weekdays.csv')
        df_wp = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
      else:
        fpath = os.path.join(config['od_average_dir'], 'od-prov-average-holidays.csv')
        df_wp = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)

      df_wp = df_wp.loc[df_wp.index.isin(hour_list, level=0)]
      df_wp.index = df_wp.index.set_levels([str(i).zfill(6) for i in df_wp.index.levels[1]], level=1)
      act_name_prov = df_prov['name'].to_list()

      ### source-dest curve
      df_wp = df_wp.loc[df_wp.index.isin(act_name_prov, level=2)]
      dfp = df_wp[df_prov.id.to_list()]
      for i,j in dfp.iterrows():
        id_reg =i[1][0:3]
        for k in j.index:
          id_reg_r = k[0][0:3]
          if id_reg_r == id_reg:
            dfp[k][i] = 0  ## remove inner mobility

      # hacking timetable with augmentation factor
      augmented = False
      for prov,val_aug in augmentation_prov.items():
        o_prov = prov.split('_')[0]
        d_prov = prov.split('_')[1]
        try:
          if (dfp.loc[(slice(None),slice(None),o_prov),dfp.columns.get_level_values(1)==d_prov].sum().values[0] > 5):
            dfp.loc[(slice(None),slice(None),o_prov),dfp.columns.get_level_values(1)==d_prov] *= val_aug
            augmented = True
        except:
          continue

      if augmented==False and len(augmentation_prov)!=0:
        return ''


      rates_per_day = 24 * 60 * 60 // self.rates_dt
      mid_start = datetime.strptime(start.strftime('%Y-%m-%d 00:00:00'), self.date_format)
      ttrates = { t : 0 for t in [ mid_start + i* timedelta(seconds=self.rates_dt) for i in range(rates_per_day) ] }
      sources = {}

      #tot_rnd_dest = df_dest.sum(axis=1).sum()
      #tot_src_rnd  = df_src.sum()
      #tot_rnd_rnd  = df_rnd.sum()
      #tot_src_dest = df.sum(axis=1).sum()
      #tot_src_dest_prov = dfp.sum(axis=1).sum()
      #tot_pawn = tot_rnd_dest + tot_src_rnd + tot_rnd_rnd + tot_src_dest + tot_src_dest_prov

      #print(f'city-city :{(tot_src_dest/tot_pawn*100):.2f} %')
      #print(f'city-rnd  :{(tot_src_rnd/tot_pawn*100):.2f} %')
      #print(f'rnd-city  :{(tot_rnd_dest/tot_pawn*100):.2f} %')
      #print(f'rnd-rnd   :{(tot_rnd_rnd/tot_pawn*100):.2f} %')
      #print(f'prov-prov   :{(tot_src_dest_prov/tot_pawn*100):.2f} %')

      datetime_hour = [datetime.strptime(start_date, self.date_fmt).replace(hour=item-1, minute=45, second=0) for item in np.arange(int(start.hour), int(stop.hour))]

      if without_rnd == False:
        ### rnd-dest curve
        for col in df_dest.columns:
          uid = col[0] # com istat code RRRPPPCCC
          rates = { t : v
            for t,v in zip(datetime_hour, df_dest[col].div(4).round().to_list())
          }

          tt = ttrates.copy()
          tt.update(rates)
          keys = sorted(tt.keys())
          last_value = list(rates.keys())[-1]+timedelta(hours=1)
          keys = [k for k in keys if k<last_value]
          for i in np.arange(1, len(keys)):
            if tt[keys[i]]==0:
              tt[keys[i]] = tt[keys[i-1]]
          name_source = col[1]
          sources.update({
            name_source+'_dest_OUT':{
              'creation_dt' : self.creation_dt,
              'creation_rate' : [ int(v) for v in tt.values() ],
              'dest_location':{
                'lat' : df_city.loc[uid, 'LAT'],
                'lon' : df_city.loc[uid, 'LON'],
              },
              'pawns': {
                'rnd_dest' : {
                  'alpha_we'       : 1.0,
                  'beta_bp_miss'   : 1.0,
                  'alpha_speed'    : 0.0,
                  'TTB'            : 5600,
                  'vmin_mps'       : 15,
                  'vmax_mps'       : 25,
                  'start_node_lid' : -1,
                  'cherry_pick'    : 'medium',
                }
              }
            }
          })

        ### src-rnd curve
        for uid in act_id_int:
          df_uid = df_src[df.index.isin([uid], level=1)]
          if len(df_uid)!=0:
            rates = { t : v
              for t,v in zip(datetime_hour, df_uid.div(4).round().to_list())
            }
            tt = ttrates.copy()
            tt.update(rates)
            keys = sorted(tt.keys())
            last_value = list(rates.keys())[-1]+timedelta(hours=1)
            keys = [k for k in keys if k<last_value]
            for i in np.arange(1, len(keys)):
              if tt[keys[i]]==0:
                tt[keys[i]] = tt[keys[i-1]]
            name_source = df_uid.index.get_level_values(2)[0]
            sources.update({
              name_source+'_src_IN':{
                'creation_dt' : self.creation_dt,
                'creation_rate' : [ int(v) for v in tt.values() ],
                'source_location':{
                  'lat' : df_city.loc[str(uid).zfill(9), 'LAT'],
                  'lon' : df_city.loc[str(uid).zfill(9), 'LON'],
                },
                'pawns': {
                  'src_rnd' : {
                    'alpha_we'     : 1.0,
                    'beta_bp_miss' : 1.0,
                    'alpha_speed'  : 0.0,
                    'TTB'          : 5600,
                    'vmin_mps'     : 15,
                    'vmax_mps'     : 25,
                    'dest'         : -1,
                    'cherry_pick'  : 'medium',
                  }
                }
              }
            })

        ### rnd-rnd curve
        rates = { t : v
          for t,v in zip(datetime_hour, df_rnd.div(4).round().values)
        }
        tt = ttrates.copy()
        tt.update(rates)
        keys = sorted(tt.keys())
        last_value = list(rates.keys())[-1]+timedelta(hours=1)
        keys = [k for k in keys if k<last_value]
        for i in np.arange(1, len(keys)):
          if tt[keys[i]]==0:
            tt[keys[i]] = tt[keys[i-1]]
        sources.update({
          'LOCALS':{
            'creation_dt' : self.creation_dt,
            'creation_rate' : [ int(v) for v in tt.values() ],
            'pawns': {
              'rnd_rnd' : {
                'alpha_we'       : 1.0,
                'beta_bp_miss'   : 1.0,
                'alpha_speed'    : 0.0,
                'vmin_mps'       : 15,
                'vmax_mps'       : 25,
                'TTB'            : 5600,
                'start_node_lid' : -1,
                'dest'           : -1,
                'cherry_pick'    : 'medium',
              }
            }
          }
        })

      ### src-dest curve
      dfgrp = df.groupby(level=['id_o','name_o'])
      for k,dfk in dfgrp:
        #print(k, dfk)
        source_lat = df_city.loc[str(k[0]).zfill(9), 'LAT']
        source_lon = df_city.loc[str(k[0]).zfill(9), 'LON']
        for j in dfk.columns:
          if dfk[j].sum()>0.0 and int(j[0])!=int(k[0]): ##la seconda condizone: mobilità locale
            dest_lat = df_city.loc[j[0], 'LAT']
            dest_lon = df_city.loc[j[0], 'LON']
            name_source = k[1].replace(' ','')+'_'+j[1].replace(' ','')
            rates = { t : v
              for t,v in zip(datetime_hour, dfk[j].div(4).round().values)
            }
            tt = ttrates.copy()
            tt.update(rates)
            keys = sorted(tt.keys())
            last_value = list(rates.keys())[-1]+timedelta(hours=1)
            keys = [k for k in keys if k<last_value]
            for i in np.arange(1, len(keys)):
              if tt[keys[i]]==0:
                tt[keys[i]] = tt[keys[i-1]]
            sources.update({
              name_source+'_IN'  : {
                'creation_dt' : self.creation_dt,
                'creation_rate' : [ int(v) for v in tt.values() ],
                'source_location' : {
                  'lat' : source_lat,
                  'lon' : source_lon
                  },
                'dest_location':{
                  'lat' : dest_lat,
                  'lon' : dest_lon,
                },
                'pawns': {
                  'scr_dest' : {
                    'alpha_we'     : 1.0,
                    'beta_bp_miss' : 0.0,
                    'alpha_speed'  : 0.0,
                    'vmin_mps'     : 15,
                    'vmax_mps'     : 25
                  }
                }
              }
            })


      ### src-dest prov curve
      dfgrp = dfp.groupby(level=['id_o','name_o'])
      for k,dfk in dfgrp:
        #print(k, dfk)
        source_lat = df_prov[df_prov.name == k[1]].Lat.values[0]
        source_lon = df_prov[df_prov.name == k[1]].Lon.values[0]
        for j in dfk.columns:
          if dfk[j].sum()>0.0: ##la seconda condizone: mobilità locale
            dest_lat = df_prov[df_prov.name == j[1]].Lat.values[0]
            dest_lon = df_prov[df_prov.name == j[1]].Lon.values[0]
            name_source = k[1].replace(' ','')+'_'+j[1].replace(' ','')
            rates = { t : v
              for t,v in zip(datetime_hour, dfk[j].div(4).round().values)
            }
            tt = ttrates.copy()
            tt.update(rates)
            keys = sorted(tt.keys())
            last_value = list(rates.keys())[-1]+timedelta(hours=1)
            keys = [k for k in keys if k<last_value]
            for i in np.arange(1, len(keys)):
              if tt[keys[i]]==0:
                tt[keys[i]] = tt[keys[i-1]]
            sources.update({
              name_source+'_IN'  : {
                'creation_dt' : self.creation_dt,
                'creation_rate' : [ int(v) for v in tt.values() ],
                'source_location' : {
                  'lat' : source_lat,
                  'lon' : source_lon
                  },
                'dest_location':{
                  'lat' : dest_lat,
                  'lon' : dest_lon,
                },
                'pawns': {
                  'scr_dest_prov' : {
                    'alpha_we'     : 1.0,
                    'beta_bp_miss' : 0.0,
                    'alpha_speed'  : 0.0,
                    'vmin_mps'     : 15,
                    'vmax_mps'     : 25
                  }
                }
              }
            })

      #print(f'Sources:     {len(sources)}')
      simc = { k : v for k, v in simtemplate.items() }
      simc['state_basename'] = f'{tag}_{timetag}/{tag}'
      simc['start_date'] = start_date
      simc['stop_date'] = stop_date
      simc['sources'] = sources
      simc['state_grid_cell_m'] = 5000
      simc['cherry_pick_mode'] = {'medium':5.0} # in km
      simc['coils_table_file'] = coilscsv
      simc['file_score_pop'] = file_ace_score
      #simc['enable_uniq_poly'] = True;
      simc['augmentation'] = augmentation
      simc['augmentation_prov'] = augmentation_prov

      # parasitic parameters, unrelated to simulation
      simc['filter_coils_plot'] = filter_coils_plot
      simc['timetag'] = timetag
      simc['tag'] = tag

      schedule.append([dfb, simc])
      print(f'Sim config created for {start_date} - {stop_date} with schedule_od_average in {(time.time()-ex_start_time):.3f} seconds')

    return schedule

  def schedule_tot(self):
    #try:
    #  schedule = self.schedule_od()
    #except:
    schedule = self.schedule_od_average()

    return schedule


if __name__ == '__main__':
  print('coming sooner or later...')
