#! /usr/bin/env python3

import json
import sys
import os
import numpy as np
from datetime import datetime, timedelta
from dateutil import tz
import pytz
import time
import pandas as pd
import glob
import matplotlib.pyplot as plt

#####################
#### logging ########
#####################
import logging
logger = logging.getLogger('conf')

##########################
###### config class ######
##########################
class conf():

  def __init__(self, config):
    logger.debug('init conf')
    self.logger = logger
    self.short_fmt = '%y%m%d_%H%M%S'
    self.date_fmt = '%Y-%m-%d %H:%M:%S'
    self.tz_rome = pytz.timezone('Europe/Rome')
    self.config = config
    self.rates_dt = 900
    self.date_format = '%Y-%m-%d %H:%M:%S'
    self.creation_dt = 30
    self.real_score = -1
    self.wdir = config['wdir']
    self.remove_local_output = config['remove_local_output']
    if not os.path.exists(self.wdir): os.mkdir(self.wdir)


  def get_basename(self, sim_uid):
    return f'{self.wdir}/sim_{sim_uid}'

  def generate(self, start_date, stop_date, sim_uid):
    logger.info(f'generating conf {start_date} - {stop_date}')

    ex_start_time = time.time()

    ### config variables
    config = self.config
    num_city = config['num_city']
    coilsdir = config['coils_table_dir']
    odavdir = config['od_average_dir']
    tag = 'od'

    ### convert datetime format to file name format
    start = pd.to_datetime(start_date + 'CET', format=self.date_fmt + '%Z')
    stop = pd.to_datetime(stop_date + 'CET', format=self.date_fmt + '%Z')
    timetag = f'{start.strftime(self.short_fmt)}_{stop.strftime(self.short_fmt)}'
    str_date = str(start.year)[2:]+str(start.month).zfill(2)+str(start.day).zfill(2)
    hour_arange = np.arange(int(start.hour)+1, int(stop.hour)+1)
    if len(hour_arange) ==0:
      hour_arange = [int(start.hour)+1]
    hour_list = [int(str(item).zfill(2)+'00') for item in hour_arange]
    wday = start.strftime('%w')


    ### match directions ###
    dirmapfile = os.path.join(coilsdir, 'coils-dir-mapping_template_0.50.csv')
    selcoil = pd.read_csv(dirmapfile, sep=';', comment='#')
    manual_drop_list = [177]
    #print(f'**** NB manually dropped coils : {manual_drop_list}')
    selcoil = selcoil[ ~selcoil.coil_id.isin(manual_drop_list)]

    coil_list = selcoil.coil_id.to_numpy()
    dir_map = {}
    for i, (cid, dirr, dirc) in selcoil.iterrows():
      #print(i, (cid, dirr, dirc))
      dirr2 = 1 if dirr == 0 else 0
      dirc2 = 'OUT' if dirc == 'IN' else 'IN'
      dir_map[f'{cid}_{dirr}'] = f'{cid}_{dirc}'
      dir_map[f'{cid}_{dirr2}'] = f'{cid}_{dirc2}'
    dir_map_inv = { v : k for k, v in dir_map.items() }

    # create direction dict for matching and filtering
    sel_coildir = [ f'{cid}_IN' for cid in selcoil.coil_id.values ]
    sel_coildir.extend([ f'{cid}_OUT' for cid in selcoil.coil_id.values ])
    sel_coildir = sorted(sel_coildir)

    coil_list = selcoil['coil_id'].to_list()
    coil_IN = [str(c)+'_IN' for c in coil_list]
    coil_OUT = [str(c)+'_OUT' for c in coil_list]
    coil_0 = [str(c)+'_0' for c in coil_list]
    coil_1 = [str(c)+'_1' for c in coil_list]
    coil_list_str = coil_IN + coil_OUT
    coil_list_num = coil_0 + coil_1

    ### read coils data ###
    #check if coils_table exixts for simulation day
    coils_tables = [os.path.basename(f) for f in glob.glob(f'{coilsdir}/coils_table*.csv')]
    day_ctformat = start_date[2:].replace('-',':').replace(':','').replace(' ','-')
    for ct in coils_tables:
      start_ct, stop_ct = ct.split('.')[0].split('_')[-2:]
      if day_ctformat >= start_ct and day_ctformat < stop_ct:
        coilscsv = f'{coilsdir}/{ct}'
        dfcoils = pd.read_csv(coilscsv, sep=';', index_col=0, parse_dates=True)
        dfcoils = dfcoils[ (dfcoils.index >= start) & (dfcoils.index < stop) ]
        dfcoils = dfcoils.interpolate()
        self.real_score = 1.0
        logger.info(f'selected coils table file: {ct}')
        break
        # per il futuro: non interpolare e verifica che questo dfcoils sia della len voluta (real-average hybrid)

    if self.real_score == -1:
      coils_aves = [os.path.basename(f) for f in glob.glob(f'{coilsdir}/coils_ave*.csv')]
      coils_aves.sort()
      day_caformat = start_date[2:].replace('-',':').replace(':','').replace(' ','-')
      ave_name_file = None
      for ca in coils_aves:
        start_ca, stop_ca = ca.split('.')[0].split('_')[-2:]
        if day_caformat > stop_ca:
          ave_name_file = ca

      if ave_name_file==None:
        try:
          ave_name_file = coils_aves[0]
        except:
          print(f'No coils average file present in "{coilsdir}"')
          exit(8)

      logger.info(f'selected coils average file: {ave_name_file}')
      coilscsv = f'{coilsdir}/{ave_name_file}'
      dfcoils = pd.read_csv(coilscsv, sep=';', index_col=0, parse_dates=True)
      dfcoils = dfcoils.interpolate()
      dfcoils=dfcoils[dfcoils.wday_n==int(wday)]
      hour_list_wday = dfcoils['time'].to_list()
      dfcoils = dfcoils.drop(['time','wday_n'], axis=1)
      day_start = datetime.strptime(f'{start.year}-{start.month}-{start.day} 00:00:00', self.date_fmt)

      datetime_list = [day_start.replace(hour=int(t.split(':')[0]), minute=int(t.split(':')[1]), second=0) for t in hour_list_wday]
      dfcoils.index = [pd.to_datetime(str(i) + 'GMT', format=self.date_fmt + '%Z') for i in datetime_list  ]
      dfcoils.index.name = 'datetime'
      dfcoils = dfcoils[ (dfcoils.index >= start) & (dfcoils.index < stop) ]
      self.real_score = 0.0

    dfcoils = dfcoils[dfcoils.columns.intersection(coil_list_num)]
    dfcoils.columns = [ dir_map[c] for c in dfcoils.columns ]
    dfcoils = dfcoils.sort_index(axis=1)

    ### read syntetic null model data ###
    synthcsv = f'{odavdir}/barriers-average.csv'
    dfsyn = pd.read_csv(synthcsv, sep=',', parse_dates=['datetime'])
    dfsyn = dfsyn[dfsyn.n_wday==int(start.weekday())]
    hour_list_wday = [f'{str(i.hour).zfill(2)}:{str(i.minute).zfill(2)}' for i in dfsyn['datetime'].to_list()]
    dfsyn = dfsyn.drop(['datetime','n_wday','timestamp'], axis=1)
    day_start = datetime.strptime(f'{start.year}-{start.month}-{start.day} 00:00:00', self.date_fmt)
    datetime_list = [day_start.replace(hour=int(t.split(':')[0]), minute=int(t.split(':')[1]), second=0) for t in hour_list_wday]
    dfsyn.index = [pd.to_datetime(str(i) + 'GMT', format=self.date_fmt + '%Z') for i in datetime_list  ]
    dfsyn.index.name = 'datetime'

    dfsyn = dfsyn[dir_map.values()].sort_index(axis=1).astype(int)
    dfsyn = dfsyn[dfsyn.columns.intersection(coil_list_str)]
    #print(dfsyn)

    ### fix time inconsistency (we can improve)
    if self.real_score == 0.0:
      dfsyn = dfsyn.iloc[4:]

    ### store metric values ###
    score_metric_dict = {}
    for c in dfcoils.columns:
      v0   = dfcoils[c].to_numpy()
      vsyn = dfsyn[c].to_numpy()
      asyn = vsyn.sum()
      a0 = v0.sum()
      ratio = a0/asyn
      score_metric_dict[c] = ratio

    ### select Prov of interest
    activity_prov_file = os.path.join(odavdir, 'prov_activity.csv')
    df_prov = pd.read_csv(activity_prov_file, sep=';')
    act_prov_id = [str(item).zfill(9) for item in df_prov['id']]
    df_prov['id'] = [ap[3:] for ap in act_prov_id]
    name_prov_outER = df_prov[df_prov['id'].astype(str).str[0:3]!='008'].name.to_list()

    ### read fit for each train coil ###
    match_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'matched_ra.csv')
    df_match = pd.read_csv(match_file, sep=';')
    df_match['is_prov'] = [1 if (r['O'] in name_prov_outER or r['D'] in name_prov_outER) else 0 for i,r in df_match.iterrows()]

    ### measure augmentation factor ###
    dict_n_aug = {}
    dict_n_aug_prov = {}
    for i in np.arange(0, len(df_match)):
      df_w = df_match.iloc[i]
      orig = df_w['O']
      dest = df_w['D']
      name_coil = df_w['Coil']
      try:
        mv = score_metric_dict[name_coil]
        a = df_w['A']
        b = df_w['B']
        n_aug = (mv-b)/a
        if df_w['is_prov'] == 0:
          dict_n_aug[f'{orig}_{dest}'] = n_aug
        else:
          dict_n_aug_prov[f'{orig}_{dest}'] = n_aug
      except:
        logger.info(f'Data from coil {name_coil} is not present in this period!')

    augmentation = dict_n_aug
    augmentation_prov = dict_n_aug_prov

    ### load sim template
    template_json = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'templates', 'check_template.json')
    with open(template_json) as tin:
      simtemplate = json.load(tin)

    ### load ace score data
    file_ace_score = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'ace_score.csv')

    ### load distance-matrix
    file_d_matrix = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'distance_matrix.csv')
    d_matrix = pd.read_csv(file_d_matrix, index_col=[0,1], header=[0,1], sep=';')
    d_matrix = d_matrix.droplevel(1)
    d_matrix.columns = d_matrix.columns.droplevel()
    d_matrix.index = d_matrix.columns
    d_matrix = d_matrix.astype(int)
    d_matrix = d_matrix.sort_index(axis=0).sort_index(axis=1)
    city_distances = d_matrix.applymap(lambda x: x).to_dict(orient='index')
    city_list = [key for key, value in city_distances.items() if key not in ["Castelfranco Emilia","Collecchio", "Sassuolo", "San Giovanni in Persiceto"]]
    # print(city_list)

    ### select City of interest
    activity_file = os.path.join(odavdir, 'city_activity.csv')
    df_city = pd.read_csv(activity_file, sep=';')
    df_city = df_city[df_city['name'].isin(city_list)].iloc[:int(num_city)]
    act_id = [str(item).zfill(9) for item in df_city['id']]
    df_city['id'] = act_id
    # print(df_city)

    ### load City geodata
    filecoords = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'italy_com.csv')
    df_coord = pd.read_csv(filecoords, sep=';', dtype={'UID':'str'})
    df_coord['id'] = df_coord['UID']
    df_city = pd.merge(df_city, df_coord[['id', 'LAT', 'LON']], how='left', on='id')
    df_city = df_city.set_index('id', drop=False)
    #print(df_city)

    #### RPC - RPC sources ###

    ## read od average file
    fpath = os.path.join(odavdir, 'od-average-n-weekday.csv')
    t = datetime.now()
    df_w = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2,3])#, parse_dates=True)#, engine='c')
    t = datetime.now() - t
    logger.info(f'read took {t}')
    od_wday = start.weekday()

    df_w = df_w.loc[od_wday,:,:].copy()
    df_w.index = df_w.index.droplevel()
    df_w = df_w.loc[df_w.index.isin(hour_list, level=0)]

    # hacking timetable with augmentation factor
    for city,val_aug in augmentation.items():
      o_city = city.split('_')[0]
      d_city = city.split('_')[1]
      df_w.loc[(slice(None),slice(None),o_city),df_w.columns.get_level_values(1)==d_city] *= val_aug

    ### rnd-dest curve
    act_id_int = [int(i) for i in act_id]
    df_wd = df_w.loc[~df_w.index.isin(act_id_int, level=1)]
    df_wd = df_wd[act_id]
    df_dest = df_wd.groupby(level='hour').sum()

    ### source-rnd curve
    df_ws = df_w.loc[df_w.index.isin(act_id_int, level=1)]
    df_src = df_ws.sort_index(axis=1).drop(columns=act_id).sum(axis=1)

    ### rnd-rnd curve
    df_wrnd = df_w.loc[~df_w.index.isin(act_id_int, level=1)]
    df_rnd = df_wrnd.sort_index(axis=1).drop(act_id,axis=1).sum(axis=1).groupby(level='hour').sum()

    ### source-dest curve
    df_w = df_w.loc[df_w.index.isin(act_id_int, level=1)]
    df = df_w[act_id]

    ### exclude cities that are too close to each other for src-dest dynamic.
    for index, row in df.iterrows():
      name_o = index[2]
      for i, value in row.iteritems():
        name_d = i[1]
        weight = city_distances.get(name_o, {}).get(name_d)
        if weight is not None and weight < 15:
          df.at[index, i] = 0

    #### RP - RP sources ###
    ## read average prov file
    fpath = os.path.join(odavdir, 'od-prov-average-n-weekday.csv')
    df_wp = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2,3], parse_dates=True)
    df_wp = df_wp.loc[od_wday,:,:].copy()
    df_wp.index = df_wp.index.droplevel()

    df_wp = df_wp.loc[df_wp.index.isin(hour_list, level=0)]
    df_wp.index = df_wp.index.set_levels([str(i).zfill(6) for i in df_wp.index.levels[1]], level=1)
    act_name_prov = df_prov['name'].to_list()

    ### source-dest curve
    df_wp = df_wp.loc[df_wp.index.isin(act_name_prov, level=2)]
    dfp = df_wp[df_prov.id.to_list()].copy()
    for i,j in dfp.iterrows():
      id_reg =i[1][0:3]
      for k in j.index:
        id_reg_r = k[0][0:3]
        if id_reg_r == id_reg:
          dfp[k][i] = 0  ## remove inner mobility

    # hacking timetable with augmentation factor
    for prov,val_aug in augmentation_prov.items():
      o_prov = prov.split('_')[0]
      d_prov = prov.split('_')[1]
      try:
        dfp.loc[(slice(None),slice(None),o_prov),dfp.columns.get_level_values(1)==d_prov] *= val_aug
      except:
        continue

    rates_per_day = 24 * 60 * 60 // self.rates_dt
    mid_start = datetime.strptime(start.strftime('%Y-%m-%d 00:00:00'), self.date_format)
    ttrates = { t : 0 for t in [ mid_start + i* timedelta(seconds=self.rates_dt) for i in range(rates_per_day) ] }
    sources = {}

    hour_arange = np.arange(int(start.hour), int(stop.hour))
    if len(hour_arange)==0:
      hour_arange = [int(start.hour)]

    if start.hour == 0:
      datetime_hour = [datetime.strptime(start_date, self.date_fmt)-timedelta(minutes=15)+timedelta(hours=int(item)) for item in hour_arange]
    else:
      datetime_hour = [datetime.strptime(start_date, self.date_fmt).replace(hour=item-1, minute=45, second=0) for item in hour_arange]

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
                  'vmax_mps'     : 25,
                  'cherry_pick'    : 'medium',
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
                  'vmax_mps'     : 25,
                  'cherry_pick'    : 'medium',
                }
              }
            }
          })
    simc = { k : v for k, v in simtemplate.items() }
    simc['state_basename'] = self.get_basename(sim_uid)
    simc['start_date'] = start_date
    simc['stop_date'] = stop_date
    simc['sources'] = sources
    simc['state_grid_cell_m'] = 5000
    simc['cherry_pick_mode'] = {'medium':10.0} # in km
    simc['file_score_pop'] = file_ace_score
    simc['enable_status'] = True
    simc['enable_uniq_poly'] = True
    simc['enable_stats'] = False
    simc['enable_population'] = False
    simc['enable_polygons'] = False

    logger.info(f'generated conf with real score {self.real_score} in {(time.time()-ex_start_time):.3f} seconds')

    return simc

  def generate_base(self, start_date, stop_date):
    logger.debug(f'generating conf {start_date} - {stop_date}')

    ex_start_time = time.time()

    ### config variables
    config = self.config
    num_city = config['num_city']
    odavdir = config['od_average_dir']
    tag = 'od'

    ### convert datetime format to file name format
    start = pd.to_datetime(start_date + 'CET', format=self.date_fmt + '%Z')
    stop = pd.to_datetime(stop_date + 'CET', format=self.date_fmt + '%Z')
    timetag = f'{start.strftime(self.short_fmt)}_{stop.strftime(self.short_fmt)}'
    str_date = str(start.year)[2:]+str(start.month).zfill(2)+str(start.day).zfill(2) # ma dai...
    hour_list = [int(str(item).zfill(2)+'00') for item in np.arange(int(start.hour)+1, int(stop.hour)+1)]
    wday = start.strftime('%w')

    augmentation = {}
    augmentation_prov = {}

    ### load sim template
    template_json = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'templates', 'check_template.json')
    with open(template_json) as tin:
      simtemplate = json.load(tin)

    ### load ace score data
    file_ace_score = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'ace_score.csv')

    ### select City of interest
    activity_file = os.path.join(odavdir, 'city_activity.csv')
    df_city = pd.read_csv(activity_file, sep=';')
    df_city = df_city.iloc[:int(num_city)]
    act_id = [str(item).zfill(9) for item in df_city['id']]
    df_city['id'] = act_id
    #print(df_city)

    ### load City geodata
    filecoords = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'italy_com.csv')
    df_coord = pd.read_csv(filecoords, sep=';', dtype={'UID':'str'})
    df_coord['id'] = df_coord['UID']
    df_city = pd.merge(df_city, df_coord[['id', 'LAT', 'LON']], how='left',on='id')
    df_city = df_city.set_index('id', drop=False)
    #print(df_city)

    #### RPC - RPC sources ###

    ## read od average file
    fpath = os.path.join(odavdir, 'od-average-n-weekday.csv')
    df_w = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2,3], parse_dates=True)
    od_wday = start.weekday()

    df_w = df_w.loc[od_wday,:,:].copy()
    df_w.index = df_w.index.droplevel()

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

    ### rnd-rnd curve
    df_wrnd = df_w.loc[~df_w.index.isin(act_id_int, level=1)]
    df_rnd = df_wrnd.sort_index(axis=1).drop(act_id,axis=1).sum(axis=1).groupby(level='hour').sum()

    ### source-dest curve
    df_w = df_w.loc[df_w.index.isin(act_id_int, level=1)]
    df = df_w[act_id]

    #### RP - RP sources ###
    ## read average prov file
    fpath = os.path.join(odavdir, 'od-prov-average-n-weekday.csv')
    df_wp = pd.read_csv(fpath, sep=';',header=[0, 1], index_col=[0,1,2,3], parse_dates=True)
    df_wp = df_wp.loc[od_wday,:,:].copy()
    df_wp.index = df_wp.index.droplevel()

    df_wp = df_wp.loc[df_wp.index.isin(hour_list, level=0)]
    df_wp.index = df_wp.index.set_levels([str(i).zfill(6) for i in df_wp.index.levels[1]], level=1)
    act_name_prov = df_prov['name'].to_list()

    ### source-dest curve
    df_wp = df_wp.loc[df_wp.index.isin(act_name_prov, level=2)]
    dfp = df_wp[df_prov.id.to_list()].copy()
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

    datetime_hour = [datetime.strptime(start_date, self.date_fmt).replace(hour=item-1, minute=45, second=0) for item in np.arange(int(start.hour), int(stop.hour))]

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
    simc = { k : v for k, v in simtemplate.items() }
    simc['state_basename'] = f'{tag}_{timetag}/{tag}'
    simc['start_date'] = start_date
    simc['stop_date'] = stop_date
    simc['sources'] = sources
    simc['state_grid_cell_m'] = 5000
    simc['cherry_pick_mode'] = {'medium':10.0} # in km
    simc['file_score_pop'] = file_ace_score
    simc['enable_uniq_poly'] = True

    logger.info(f'generated conf with real score {self.real_score} in {(time.time()-ex_start_time):.3f} seconds', self.logger)

    return simc

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cfg', help='prepare config file', required=True)
  args = parser.parse_args()

  with open(args.cfg) as cfgfile:
    config = json.load(cfgfile)

  try:
    cfg_sim = conf(config)

    start_date = config['start_date']
    stop_date = config['stop_date']

    sim = cfg_sim.generate(start_date, stop_date, 100)
    real_score = cfg_sim.real_score

    with open('sim_walker.json', 'w') as simout:
      json.dump(sim, simout, indent=2)
  except Exception as e:
    print('main EXC : {}'.format(e))
