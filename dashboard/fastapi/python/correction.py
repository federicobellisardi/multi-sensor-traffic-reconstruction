#!/usr/bin/env python3

from collections import defaultdict
from numpy.lib.shape_base import column_stack
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import numpy as np
# import datetime
from datetime import date, datetime
from glob import glob

class SimPostCorrection():

  def __init__(self, config, sim_basename, debug_times=False):
    self.config = config
    self.counter_threshold = 5
    self.recursion_threshold = 1
    self.recursion_max_depth = 5

    self.vars_dir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars')
    self.sim_basename = sim_basename

    if debug_times:
      self.global_time_debug = [
        # pd.to_datetime('2022-06-22 05:00:00'),
        # pd.to_datetime('2022-06-22 08:00:00'),
        pd.to_datetime('2022-06-22 15:00:00'),
        # pd.to_datetime('2022-06-22 20:00:00'),
      ]
    else:
      self.global_time_debug = []

    self.init_data()

  def init_data(self):
    # network support containers
    network_pro_file = f'{self.vars_dir}/carto/er-speed.pro'
    dfn = pd.read_csv(network_pro_file, sep=r"\s+", engine='python')
    # print(dfn)
    polymap = defaultdict(lambda : {})
    node_adlist = defaultdict(lambda : [])
    poly_list = {}
    poly_l2c = {}
    poly_c2l = {}
    plid = 0
    for p,n1,n2 in dfn[['#poly_cid', 'node_front_cid', 'node_tail_cid']].values:
      polymap[n1][n2] = p
      polymap[n2][n1] = p

      node_adlist[n1].append([p, n2])
      node_adlist[n2].append([p, n1])

      poly_list[p] = (n1,n2)
      poly_l2c[plid] = p
      poly_c2l[p] = plid
      plid += 1

    poly_adlist = defaultdict(lambda : set())
    for _, links in node_adlist.items():
      for p, _ in links:
        for pp, _ in links:
          if pp != p:
            poly_adlist[p].add(pp)

    dir_adlist = defaultdict(lambda : [])
    for p, (nf,nt) in poly_list.items():
      for pl, nl in node_adlist[nf]:
        if nl == nt: continue
        if nl == poly_list[pl][0]:
          dir_adlist[f'{p}_OUT'].append(f'{pl}_OUT')
          dir_adlist[f'{p}_IN'].append(f'{pl}_IN')
        else:
          dir_adlist[f'{p}_OUT'].append(f'{pl}_IN')
          dir_adlist[f'{p}_IN'].append(f'{pl}_OUT')

      for pl, nl in node_adlist[nt]:
        if nl == nf: continue
        if nl == poly_list[pl][0]:
          dir_adlist[f'{p}_OUT'].append(f'{pl}_IN')
          dir_adlist[f'{p}_IN'].append(f'{pl}_OUT')
        else:
          dir_adlist[f'{p}_OUT'].append(f'{pl}_OUT')
          dir_adlist[f'{p}_IN'].append(f'{pl}_IN')
    #print(dir_adlist)

    # metadata coil-poly support containers
    barriergeodata_file = f'{self.vars_dir}/extra/er_barriers_cartodata.csv'
    dfb = pd.read_csv(barriergeodata_file, sep=';')
    #print(dfb)
    poly2coil = {}
    coil2poly = {}
    for coil, plid in dfb[['tag', 'poly_lid']].values:
      pcid = poly_l2c[plid]
      coil2poly[coil] = pcid
      poly2coil[pcid] = coil

    # uniq input file
    unique_file = glob(f'{self.sim_basename}_uniq_*.csv')[0]
    self.unique_file = unique_file
    dfu = pd.read_csv(unique_file, sep=';', parse_dates=True)
    dfu.oneway = dfu.oneway.replace('FT', 'IN').replace('TF', 'OUT')
    dfu['poly_dir'] = [ f'{poly}_{dir}' for poly, dir in dfu[['poly_cid', 'oneway']].values ]
    dfu = dfu.drop(columns=['poly_cid', 'poly_lid', 'oneway']).set_index('poly_dir').T
    dfu = dfu.stack().reset_index()
    dfu[['poly_cid', 'direction']] = dfu.poly_dir.str.split('_', 1, expand=True)
    dfu.poly_cid = dfu.poly_cid.astype('int')
    dfu = dfu.rename(columns={'level_0':'datetime', 0:'counter'})
    dfu.datetime = pd.to_datetime(dfu.datetime)

    # uniq processing for plots
    dfu1 = pd.read_csv(unique_file, sep=';', parse_dates=True)
    dfu1.oneway = dfu1.oneway.replace('FT', 'IN').replace('TF', 'OUT')
    dfu1['poly_dir'] = [ f'{poly}_{dir}' for poly, dir in dfu1[['poly_cid', 'oneway']].values ]
    dfu1 = dfu1.drop(columns=['poly_cid', 'poly_lid', 'oneway']).set_index('poly_dir').T
    dfu1.index = pd.to_datetime(dfu1.index)

    # synth barriers file
    barriers_synth = glob(f'{self.sim_basename}_barriers_*.csv')[0]
    dfs = pd.read_csv(barriers_synth, sep=';', parse_dates=True).drop(columns='timestamp').set_index('datetime')

    # list of correction coils direction metadata
    pivot_file = f'{self.vars_dir}/extra/correction-pivot-mapping.csv'
    dfp = pd.read_csv(pivot_file, sep=';')
    # print(dfp)
    pivotmap = {}
    for coil, dr, dc in dfp[['coil_id', 'dir_reg', 'dir_carto']].values:
      dr1 = 0 if dr == 0 else 1
      dc1 = 'IN' if dc == 'IN' else 'OUT'
      dr2 = 1 if dr == 0 else 0
      dc2 = 'OUT' if dc == 'IN' else 'IN'
      pivotmap[f'{coil}_{dr1}'] = f'{coil}_{dc1}'
      pivotmap[f'{coil}_{dr2}'] = f'{coil}_{dc2}'

    # coil data (sampling 15min)
    ## search for coils data file
    files = sorted(glob(f'{self.config["coils_table_dir"]}/coils_table_*.csv'))
    start_u = dfu.datetime.min()
    stop_u = dfu.datetime.max()
    barriers_coils_file = ''
    for f in files:
      start, stop = f.replace('.csv', '').split('_')[-2:]
      start = pd.to_datetime(start, format='%y%m%d-%H%M%S')
      stop = pd.to_datetime(stop, format='%y%m%d-%H%M%S')
      if start_u >= start and stop_u <= stop:
        barriers_coils_file = f
        break
    
    ## prepare coil data
    Y = 2000 # dummy leap year to allow input X-02-29 (leap day)
    seasons = [('winter', (date(Y,  1,  1),  date(Y,  3, 20))),
               ('spring', (date(Y,  3, 21),  date(Y,  6, 20))),
               ('summer', (date(Y,  6, 21),  date(Y,  9, 22))),
               ('autumn', (date(Y,  9, 23),  date(Y, 12, 20))),
               ('winter', (date(Y, 12, 21),  date(Y, 12, 31)))]

    def get_season(t):
      if isinstance(t, datetime):
        t = t.date()
      t = t.replace(year=Y)
      return next(season for season, (start, end) in seasons if start <= t <= end)

    def read_data(season, coils_ave_files, coils_std_files):
      time_param = 0.7                                          #TODO: Study a way to weight the past years and the present year data
      recorded_year = [pd.to_datetime(f_ave.replace('.csv', '').split('_')[-2:][0], format='%y%m%d-%H%M%S').year for f_ave in coils_ave_files]
      last_year = max(recorded_year)
      
      for f_std in coils_std_files:
        start, stop = f_std.replace('.csv', '').split('_')[-2:]
        start = pd.to_datetime(start, format='%y%m%d-%H%M%S')
        stop = pd.to_datetime(stop, format='%y%m%d-%H%M%S')
        if start.year == last_year:
          std_dev_coils_file = f_std
          dferr_this_year = pd.read_csv(std_dev_coils_file, sep=';')
          dferr_this_year = dferr_this_year.loc[dferr_this_year['season'] == season ].set_index(['wday', 'wday_n', 'time', 'season'])
          df_weight_this = 1/dferr_this_year#.iloc[:,4:]
          df_weight_this[np.isnan(df_weight_this) | (df_weight_this == 0)] = 0

        else:
          std_dev_coils_file = f_std
          dferr_last_years = pd.read_csv(std_dev_coils_file, sep=';')
          dferr_last_years = dferr_last_years.loc[dferr_last_years['season'] == season ].set_index(['wday', 'wday_n', 'time', 'season'])
          df_weight_last = 1 / dferr_last_years#.iloc[:,4:]
          df_weight_last[np.isnan(df_weight_last) | (df_weight_last == 0)] = 0

      for f_ave in coils_ave_files:
        start, stop = f_ave.replace('.csv', '').split('_')[-2:]
        start = pd.to_datetime(start, format='%y%m%d-%H%M%S')
        stop = pd.to_datetime(stop, format='%y%m%d-%H%M%S')
        if start.year == last_year:
          barriers_coils_file = f_ave
          dfave_this_year = pd.read_csv(barriers_coils_file, sep=';')
          dfave_this_year = dfave_this_year.loc[dfave_this_year['season'] == season ].set_index(['wday', 'wday_n', 'time', 'season'])
          dfave_this_year.fillna(0, inplace=True)
        else:
          barriers_coils_file = f_ave
          dfave_last_years = pd.read_csv(barriers_coils_file, sep=';')
          dfave_last_years = dfave_last_years.loc[dfave_last_years['season'] == season ].set_index(['wday', 'wday_n', 'time', 'season'])
          dfave_last_years.fillna(0, inplace=True)

      dfc = (time_param * dfave_this_year * df_weight_this + (1-time_param) * dfave_last_years * df_weight_last) / (time_param * df_weight_this + (1-time_param) * df_weight_last)
      dfc = dfc.reset_index(drop=False)
      return dfc
    
    def fill_with_ave():
      actual_season = get_season(start_u.date())
      barriers_coils_files = sorted(glob(f'{self.config["coils_table_dir"]}/coils_ave_*.csv'), reverse=True)
      std_dev_coils_files = sorted(glob(f'{self.config["coils_table_dir"]}/coils_std_*.csv'), reverse=True)
      dfc = read_data(actual_season, barriers_coils_files, std_dev_coils_files)
      wday = int(start_u.strftime('%w').lower())
      dfc = dfc[ dfc.wday_n == wday ]
      dfc['datetime'] = pd.to_datetime([ f'{start_u.date()} {t}:00' for t in dfc.time.values ])
      dfc = dfc.drop(columns=['wday', 'wday_n', 'time', 'season']).set_index('datetime').tz_localize('UTC')
      return dfc

    def process_dataframe(df, pivotmap=None):
      if pivotmap is not None:
        df.columns = [pivotmap[c] if c in pivotmap else c for c in df.columns]
      df = df[[c for c in df.columns if c.endswith('_IN') or c.endswith('_OUT')]]
      df = df.dropna(axis=1, how='all')
      df.columns.name = 'coils'
      df.index = pd.to_datetime(df.index)
      df = df.tz_localize(None)
      return df
    
    if barriers_coils_file == '':
      dfc = fill_with_ave()
    else:
      dfc = pd.read_csv(barriers_coils_file, sep=';').set_index('datetime')
    df_fill = fill_with_ave()

    df_fill = process_dataframe(df_fill, pivotmap)
    dfc = process_dataframe(dfc, pivotmap)
    dfc = dfc[ (dfc.index >= dfs.index[0]) & (dfc.index <= dfs.index[-1]) ]
    dfc = dfc.fillna(df_fill)
    dfc = dfc.interpolate()

    c_list = list(set([ int(c.split('_')[0]) for s in poly2coil.values() for c in dfc.columns if c.startswith(f'{s}_')]))
    if len(c_list) != len(poly2coil.values()):
      poly2coil = {key: value for key, value in poly2coil.items() if value in c_list}
    
    #prepare noturn file
    noturn_dir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra')
    noturn_file = f'{noturn_dir}/noturn.csv'
    noturn_df = pd.read_csv(noturn_file, header=[0], sep=';')
    noturn_df.reset_index(drop=True)
    noturn_dict = dict()
    for (key, value) in noturn_df.groupby("cid1"):
      polysta = list(value.cid2.values) 
      noturn_dict[key] = polysta

    #prepare closed poly
    patch_dir = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra')
    patched_file = f'{patch_dir}/er.file_shadow'
    patched_df = pd.read_csv(patched_file, header=[0], sep=';')
    patched_df = patched_df.drop(columns='ow')
    patched_df.reset_index(drop=True)
    patched_list = list(patched_df.cid)

    # add std_dev
    std_dev_coils_file = sorted(glob(f'{self.config["coils_table_dir"]}/coils_std_*.csv'))[-1]
    df_std = pd.read_csv(std_dev_coils_file, sep=';')
    wday = int(start_u.strftime('%w').lower())
    df_std = df_std[ df_std.wday_n == wday ]
    df_std['datetime'] = pd.to_datetime([ f'{start_u.date()} {t}:00' for t in df_std.time.values ])
    df_std = df_std.drop(columns=['wday', 'wday_n', 'time']).set_index('datetime').tz_localize('UTC')
    df_std.columns = [ pivotmap[c] if c in pivotmap else c for c in df_std.columns]
    df_std = df_std[[ c for c in df_std.columns if c.endswith('_IN') or c.endswith('_OUT')]]
    df_std.columns.name = 'coils'
    df_std.index = pd.to_datetime(df_std.index)
    df_std = df_std.tz_localize(None)
    df_std = df_std.interpolate()
    df_std = df_std[ (df_std.index >= dfs.index[0]) & (df_std.index <= dfs.index[-1]) ]

    for col in df_std:
      try:
        std_col = df_std[col]
        mean_col = dfc[col] 
        std_mean = std_col.mean(skipna=True)
        mean_mean = mean_col.mean(skipna=True)
        ratio = std_mean / mean_mean
        std_col = std_col.fillna(mean_col * ratio)
        df_std[col] = std_col
      except Exception as e:
        # print(f'Exception df_std: {e}')
        pass

    dfc_overrated = dfc + df_std
    dfc_underrated = dfc - df_std

    # dfs-dfc harmonization
    ## enforce same columns after nan removal
    dfs = dfs[ dfc.columns ]
    dfc = dfc.dropna(how='all', axis=1)
    dfc = dfc.astype('float')
    dfs = dfs[ dfc.columns ]
    dfs = dfs.astype('float')
    ## enforce same time sampling
    if len(dfc) > len(dfs):
      dfc = dfc.resample('1h').sum() # @TODO: change hardcoded 1h to computed dt from dfs
      dfc_overrated = dfc_overrated.resample('1h').sum()
      dfc_overrated = dfc_overrated.loc[:, (dfc_overrated != 0).any(axis=0)]
      dfc_underrated = dfc_underrated.resample('1h').sum()
      dfc_underrated = dfc_underrated.loc[:, (dfc_underrated != 0).any(axis=0)]
    dfs = dfs.set_index(dfc.index)

    # save stuff
    self.poly_list = poly_list
    self.poly_l2c = poly_l2c
    self.poly_c2l = poly_c2l
    self.polymap = polymap
    self.node_adlist = node_adlist
    self.poly_adlist = poly_adlist
    self.dir_adlist = dir_adlist
    self.dfs = dfs
    self.dfc = dfc
    self.date = df_std.index[0].date()
    self.dfc_over = dfc_overrated
    self.dfc_under = dfc_underrated
    self.dfb = dfb
    self.dfu = dfu
    self.dfu1 = dfu1
    self.coil2poly = coil2poly
    self.poly2coil = poly2coil
    self.noturn_dict = noturn_dict
    self.patched_list = patched_list
    
  def correct(self, sel_coil = []):
    # load stuff
    dfs = self.dfs
    dfc = self.dfc
    dfb = self.dfb
    dfu = self.dfu
    poly_list = self.poly_list
    poly_l2c = self.poly_l2c
    poly_c2l = self.poly_c2l
    node_adlist = self.node_adlist
    polymap = self.polymap
    p2c = self.poly2coil

    # filter selected coils
    if len(sel_coil) == 0:
      sel_coil = dfb.tag.values
    else:
      sel_coil = sel_coil
    dfs = dfs[[ c for s in sel_coil for c in dfs.columns if c.startswith(f'{s}_') ]]
    dfc = dfc[[ c for s in sel_coil for c in dfc.columns if c.startswith(f'{s}_') ]]

    dfuc = dfu.copy()
    dfuc['coil'] = dfuc['poly_cid'].map(p2c)
    dfuc = dfuc.loc[dfuc['coil'].notnull()]
    dfuc['coil'] = dfuc['coil'].astype(int).astype(str) + '_' + dfuc['direction']
    dfuc = dfuc.pivot(index='datetime', columns = "coil", values = "counter")
    dfuc = dfuc[[ c for s in sel_coil for c in dfs.columns if c.startswith(f'{s}_') ]]
# compute relative delta
    dfr = dfs / dfuc.replace(0,1)
    dfd = (dfc * dfr - dfs) / dfs.replace(0,1)

    dfd = dfd.stack().reset_index()
    dfd = dfd.rename(columns={'coils':'coil_dir', 'level_1':'coil_dir', 0:'counter'})
    dfd[['coil_id', 'direction']] = dfd.coil_dir.str.split('_', 1, expand=True)
    dfd.coil_id = dfd.coil_id.astype('int')
    dfd = dfd.merge(dfb[['tag', 'poly_lid']], how='left', left_on='coil_id', right_on='tag')
    dfd['n1'] = [ poly_list[poly_l2c[p]][0] if d == 'IN' else poly_list[poly_l2c[p]][1] for p,d in dfd[['poly_lid', 'direction']].values ]
    dfd['n2'] = [ poly_list[poly_l2c[p]][1] if d == 'IN' else poly_list[poly_l2c[p]][0] for p,d in dfd[['poly_lid', 'direction']].values ]
    dfd.datetime = pd.to_datetime(dfd.datetime)

    if len(self.global_time_debug):
      dfd = dfd[ dfd['datetime'].isin(self.global_time_debug)]

    delta = defaultdict(lambda : defaultdict(lambda : {}))
    for t,n1,n2,c in dfd[['datetime', 'n1', 'n2', 'counter']].values:
      delta[t][n1][n2] = c

    #################################################
    # if 1:
      # t = pd.to_datetime('2022-06-22 15:00:00')
      # print('dbs\n', dfs[ (dfs.index == t) ])
      # print('***************************')
      # print('dbc\n', dfc[ (dfc.index == t) ])
      # print('***************************')
      # print('dbd\n', dfd[ (dfd.datetime == t) ])
    #################################################

    # prepare synth data for ratio evaluation
    dfs1 = dfs.stack().reset_index()
    dfs1 = dfs1.rename(columns={'coils':'coil_dir', 'level_1':'coil_dir', 0:'counter'})
    dfs1[['coil_id', 'direction']] = dfs1.coil_dir.str.split('_', 1, expand=True)
    dfs1.coil_id = dfs1.coil_id.astype('int')
    dfs1 = dfs1.merge(dfb[['tag', 'poly_lid']], how='left', left_on='coil_id', right_on='tag')
    dfs1['n1'] = [ poly_list[poly_l2c[p]][0] if d == 'IN' else poly_list[poly_l2c[p]][1] for p,d in dfs1[['poly_lid', 'direction']].values ]
    dfs1['n2'] = [ poly_list[poly_l2c[p]][1] if d == 'IN' else poly_list[poly_l2c[p]][0] for p,d in dfs1[['poly_lid', 'direction']].values ]
    dfs1.datetime = pd.to_datetime(dfs1.datetime)
    synth = defaultdict(lambda : defaultdict(lambda : {}))
    for t,n1,n2,c in dfs1[['datetime', 'n1', 'n2', 'counter']].values:
      synth[t][n1][n2] = c

    # weight preparation
    ## debug times
    if len(self.global_time_debug):
      dfwe = dfu[ dfu.datetime.isin(self.global_time_debug) ].copy()
    else:
      dfwe = dfu.copy()
    dfwe['n1'] = [ poly_list[p][0] if d == 'IN' else poly_list[p][1] for p,d in dfwe[['poly_cid', 'direction']].values ]
    dfwe['n2'] = [ poly_list[p][1] if d == 'IN' else poly_list[p][0] for p,d in dfwe[['poly_cid', 'direction']].values ]
    # print(dfwe)
    dfn = pd.DataFrame([ [n1,n2] for n1, nlist in node_adlist.items() for _, n2 in nlist ], columns=['n', 'n_link'])
    # print(dfn)
    ## forward weight matrix
    dft = dfwe.merge(dfn, how='outer', left_on='n2', right_on='n').drop(columns=['n'])
    dft = dft[ dft.n1 != dft.n_link ]
    dft = dft.merge(dfwe[['datetime', 'n1', 'n2', 'counter']], how='left', left_on=['datetime', 'n2', 'n_link'], right_on=['datetime', 'n1', 'n2'], suffixes=('', '_w') ).drop(columns=['n1_w', 'n2_w'])
    dftot = dft[['datetime','n1','n2','counter_w']].groupby(['datetime','n1','n2']).agg({
      'counter_w':('sum','count'),
    })
    dftot.columns = dftot.columns.droplevel()
    dftot = dftot.reset_index()
    dft = dft.merge(dftot, how='left', left_on=['datetime','n1','n2'], right_on=['datetime','n1','n2'], suffixes=('', '_w'))
    dft['weight'] = dft.counter_w / dft['sum']
    dft.weight = dft.weight.fillna(1 / dft['count'])
    dft = dft[['datetime', 'n1', 'n2', 'n_link', 'counter', 'weight']]
    # print(dft)
   
    ## backward weight matrix
    dftb = dfwe.merge(dfn, how='outer', left_on='n1', right_on='n').drop(columns=['n'])
    dftb = dftb[ dftb.n2 != dftb.n_link ]
    dftb = dftb.rename(columns={'n_link':'n_back'})
    dftb = dftb[['datetime', 'poly_dir', 'counter', 'poly_cid', 'direction', 'n_back', 'n1', 'n2']]
    dftb = dftb.merge(dfwe[['datetime', 'n1', 'n2', 'counter']], how='left',
                      left_on=['datetime', 'n_back', 'n1'],
                      right_on=['datetime', 'n1', 'n2'],
                      suffixes=('', '_w')
    ).drop(columns=['n1_w', 'n2_w'])
    dftotb = dftb[['datetime','n1','n2','counter_w']].groupby(['datetime','n1','n2']).agg({
      'counter_w':('sum','count'),
    })
    dftotb.columns = dftotb.columns.droplevel()
    dftotb = dftotb.reset_index()
    dftb = dftb.merge(dftotb, how='left', left_on=['datetime','n1','n2'], right_on=['datetime','n1','n2'], suffixes=('', '_w'))
    dftb['weight'] = dftb.counter_w / dftb['sum']
    dftb.weight = dftb.weight.fillna(1 / dftb['count'])
    dftb = dftb[['datetime', 'n_back', 'n1', 'n2', 'counter', 'weight']]

    # populate data wrappers
    self.we = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : {})))
    counters = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
    self.newcnt = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
    ratio_su = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
    for t, n1, n2, nlink, c, w in dft.values:
      self.we[t][n1][n2][nlink] = w
      counters[t][n1][n2] = c
      self.newcnt[t][n1][n2] = c
    self.web = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : {})))
    for t, nback, n1, n2, c, w in dftb.values:
      self.web[t][nback][n1][n2] = w

    # correction recursion loop
    print('Computing recursive correction')

    for t, coil, p, n1, n2 in dfd[[ 'datetime', 'coil_id', 'poly_lid', 'n1', 'n2']].values:
      # if coil == 321:
      #   # print('Skippo: ', coil)
      #   continue

      # ratio_su = max(counters[t][n1][n2], 1) / max(synth[t][n1][n2], 1)
      localdelta = counters[t][n1][n2] * delta[t][n1][n2] #/ ratio_su
      newcnt = self.newcnt[t][n1][n2] + localdelta

      if newcnt > 0:
        self.newcnt[t][n1][n2] = newcnt
        self.apply_correction_recursive(t, n1, n2, localdelta, [])
        self.apply_correction_recursive_backward(t, n1, n2, localdelta, [])

    # convert correction result to uniq csv format
    newdata = []
    for t, v in self.newcnt.items():
      for n1,v1 in v.items():
        for n2,v2 in v1.items():
          newdata.append([t, n1, n2, int(v2)])
    df = pd.DataFrame(newdata, columns=['datetime', 'n1', 'n2', 'cnt'])
    df.loc[df['cnt'] < 0, 'cnt'] = 0
    df['oneway'] = [ 'FT' if n1 == poly_list[polymap[n1][n2]][0] else 'TF' for n1, n2 in df[['n1', 'n2']].values ]
    df['poly_cid'] = [ polymap[n1][n2] for n1, n2 in df[['n1', 'n2']].values ]
    df = df.drop(columns=['n1', 'n2']).set_index(['poly_cid', 'oneway', 'datetime']).unstack(level=2)
    df.columns = df.columns.droplevel()
    df = df.reset_index()
    df['poly_lid'] = [ poly_c2l[p] for p in df.poly_cid.values ]
    df = df[['poly_lid', 'poly_cid', 'oneway'] + sorted([ c for c in df.columns if not isinstance(c, str) ])]
    df = df.sort_values(by=['oneway', 'poly_cid']).fillna(0)
    corrected_file = f'{self.unique_file}.corrected'
    df.to_csv(corrected_file, sep=';', index=False)

    return corrected_file

  def correct_prov(self, sel_coil = []):
    #load stuff
    dfs = self.dfs
    dfc = self.dfc
    dfc_under = self.dfc_under
    dfc_over = self.dfc_over
    dfb = self.dfb
    dfu = self.dfu
    poly_list = self.poly_list
    poly_l2c = self.poly_l2c
    poly_c2l = self.poly_c2l
    node_adlist = self.node_adlist
    polymap = self.polymap

    df_list = [dfc_under, dfc_over]

    # filter selected coils
    if len(sel_coil) == 0:
      sel_coil = dfb.tag.values
    else:
      sel_coil = sel_coil

    df_range = []
    for i, dfc in enumerate(df_list):  
      dfs = dfs[[ c for s in sel_coil for c in dfs.columns if c.startswith(f'{s}_') ]]
      dfc = dfc[[ c for s in sel_coil for c in dfc.columns if c.startswith(f'{s}_') ]]

      # compute relative delta
      dfd = (dfc - dfs) / dfs.replace(0,1)
      dfd = dfd.stack().reset_index()
      dfd = dfd.rename(columns={'coils':'coil_dir', 'level_1':'coil_dir', 0:'counter'})
      dfd[['coil_id', 'direction']] = dfd.coil_dir.str.split('_', 1, expand=True)
      dfd.coil_id = dfd.coil_id.astype('int')
      dfd = dfd.merge(dfb[['tag', 'poly_lid']], how='left', left_on='coil_id', right_on='tag')
      dfd['n1'] = [ poly_list[poly_l2c[p]][0] if d == 'IN' else poly_list[poly_l2c[p]][1] for p,d in dfd[['poly_lid', 'direction']].values ]
      dfd['n2'] = [ poly_list[poly_l2c[p]][1] if d == 'IN' else poly_list[poly_l2c[p]][0] for p,d in dfd[['poly_lid', 'direction']].values ]
      dfd.datetime = pd.to_datetime(dfd.datetime)
      if len(self.global_time_debug):
        dfd = dfd[ dfd['datetime'].isin(self.global_time_debug)]

      delta = defaultdict(lambda : defaultdict(lambda : {}))
      for t,n1,n2,c in dfd[['datetime', 'n1', 'n2', 'counter']].values:
        delta[t][n1][n2] = c

      #################################################
      if 0:
        t = pd.to_datetime('2020-02-10 06:00:00')
        print('dbg', dfs[ (dfs.index == t) ])
        print('dbg', dfc[ (dfc.index == t) ])
        print('dbg', dfd[ (dfd.datetime == t) ])
      #################################################

      # prepare synth data for ratio evaluation
      dfs1 = dfs.stack().reset_index()
      dfs1 = dfs1.rename(columns={'coils':'coil_dir', 'level_1':'coil_dir', 0:'counter'})
      dfs1[['coil_id', 'direction']] = dfs1.coil_dir.str.split('_', 1, expand=True)
      dfs1.coil_id = dfs1.coil_id.astype('int')
      dfs1 = dfs1.merge(dfb[['tag', 'poly_lid']], how='left', left_on='coil_id', right_on='tag')
      dfs1['n1'] = [ poly_list[poly_l2c[p]][0] if d == 'IN' else poly_list[poly_l2c[p]][1] for p,d in dfs1[['poly_lid', 'direction']].values ]
      dfs1['n2'] = [ poly_list[poly_l2c[p]][1] if d == 'IN' else poly_list[poly_l2c[p]][0] for p,d in dfs1[['poly_lid', 'direction']].values ]
      dfs1.datetime = pd.to_datetime(dfs1.datetime)

      synth = defaultdict(lambda : defaultdict(lambda : {}))
      for t,n1,n2,c in dfs1[['datetime', 'n1', 'n2', 'counter']].values:
        synth[t][n1][n2] = c

      # weight preparation
      ## debug times
      if len(self.global_time_debug):
        dfwe = dfu[ dfu.datetime.isin(self.global_time_debug) ].copy()
      else:
        dfwe = dfu.copy()
      dfwe['n1'] = [ poly_list[p][0] if d == 'IN' else poly_list[p][1] for p,d in dfwe[['poly_cid', 'direction']].values ]
      dfwe['n2'] = [ poly_list[p][1] if d == 'IN' else poly_list[p][0] for p,d in dfwe[['poly_cid', 'direction']].values ]
      # print(dfwe)
      dfn = pd.DataFrame([ [n1,n2] for n1, nlist in node_adlist.items() for _, n2 in nlist ], columns=['n', 'n_link'])

      ## forward weight matrix
      dft = dfwe.merge(dfn, how='outer', left_on='n2', right_on='n').drop(columns=['n'])
      dft = dft[ dft.n1 != dft.n_link ]
      dft = dft.merge(dfwe[['datetime', 'n1', 'n2', 'counter']], how='left', left_on=['datetime', 'n2', 'n_link'], right_on=['datetime', 'n1', 'n2'], suffixes=('', '_w') ).drop(columns=['n1_w', 'n2_w'])
      dftot = dft[['datetime','n1','n2','counter_w']].groupby(['datetime','n1','n2']).agg({
        'counter_w':('sum','count'),
      })
      dftot.columns = dftot.columns.droplevel()
      dftot = dftot.reset_index()
      # print('tot\n',dftot)

      dft = dft.merge(dftot, how='left', left_on=['datetime','n1','n2'], right_on=['datetime','n1','n2'], suffixes=('', '_w'))
      dft['weight'] = dft.counter_w / dft['sum']
      dft.weight = dft.weight.fillna(1 / dft['count'])
      dft = dft[['datetime', 'n1', 'n2', 'n_link', 'counter', 'weight']]
      #print(dft)
      ## backward weight matrix
      dftb = dfwe.merge(dfn, how='outer', left_on='n1', right_on='n').drop(columns=['n'])
      dftb = dftb[ dftb.n2 != dftb.n_link ]
      dftb = dftb.rename(columns={'n_link':'n_back'})
      dftb = dftb[['datetime', 'poly_dir', 'counter', 'poly_cid', 'direction', 'n_back', 'n1', 'n2']]
      dftb = dftb.merge(dfwe[['datetime', 'n1', 'n2', 'counter']], how='left',
                        left_on=['datetime', 'n_back', 'n1'],
                        right_on=['datetime', 'n1', 'n2'],
                        suffixes=('', '_w')
      ).drop(columns=['n1_w', 'n2_w'])
      dftotb = dftb[['datetime','n1','n2','counter_w']].groupby(['datetime','n1','n2']).agg({
        'counter_w':('sum','count'),
      })
      dftotb.columns = dftotb.columns.droplevel()
      dftotb = dftotb.reset_index()
      dftb = dftb.merge(dftotb, how='left', left_on=['datetime','n1','n2'], right_on=['datetime','n1','n2'], suffixes=('', '_w'))
      dftb['weight'] = dftb.counter_w / dftb['sum']
      dftb.weight = dftb.weight.fillna(1 / dftb['count'])
      dftb = dftb[['datetime', 'n_back', 'n1', 'n2', 'counter', 'weight']]

      # populate data wrappers
      self.we = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : {})))
      counters = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
      self.newcnt = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
      ratio_su = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : 0)))
      for t, n1, n2, nlink, c, w in dft.values:
        self.we[t][n1][n2][nlink] = w
        counters[t][n1][n2] = c
        self.newcnt[t][n1][n2] = c
      self.web = defaultdict(lambda : defaultdict(lambda : defaultdict(lambda : {})))
      for t, nback, n1, n2, c, w in dftb.values:
        self.web[t][nback][n1][n2] = w

      # correction recursion loop
      evaluation_type = {0:'counter min', 1:'counter max'}
      print(f'Computing recursive correction for {evaluation_type[i]}')
      for t, coil, p, n1, n2 in dfd[[ 'datetime', 'coil_id', 'poly_lid', 'n1', 'n2']].values:
        ratio_su = max(counters[t][n1][n2], 1) / max(synth[t][n1][n2], 1)
        localdelta = counters[t][n1][n2] * delta[t][n1][n2] / ratio_su
        newcnt = self.newcnt[t][n1][n2] + localdelta

        if newcnt > 0:
          self.newcnt[t][n1][n2] = newcnt
          self.apply_correction_recursive(t, n1, n2, localdelta, [])
          # self.apply_correction_recursive_backward(t, n1, n2, localdelta, [])

      # convert correction result to uniq csv format
      newdata = []
      for t, v in self.newcnt.items():
        for n1,v1 in v.items():
          for n2,v2 in v1.items():
            newdata.append([t, n1, n2, v2])
      df = pd.DataFrame(newdata, columns=['datetime', 'n1', 'n2', 'cnt'])

      df['oneway'] = [ 'FT' if n1 == poly_list[polymap[n1][n2]][0] else 'TF' for n1, n2 in df[['n1', 'n2']].values ]
      df['poly_cid'] = [ polymap[n1][n2] for n1, n2 in df[['n1', 'n2']].values ]
      df = df.drop(columns=['n1', 'n2']).set_index(['poly_cid', 'oneway', 'datetime']).unstack(level=2)
      df.columns = df.columns.droplevel()
      df = df.reset_index()
      df['poly_lid'] = [ poly_c2l[p] for p in df.poly_cid.values ]
      df = df[['poly_lid', 'poly_cid', 'oneway'] + sorted([ c for c in df.columns if not isinstance(c, str) ])]
      df = df.sort_values(by=['oneway', 'poly_cid'])

      df = df.round(0)
      df_range.append(df)

    df_under = pd.DataFrame(df_range[0])
    df_over = pd.DataFrame(df_range[1])

    df_both_ls = [] 
    for df in [df_under, df_over]:
      df = df.groupby(['poly_cid', 'poly_lid']).sum()
      df['counter'] = df.sum(axis=1)
      df.reset_index(inplace=True)
      df = df[['poly_cid', 'poly_lid', 'counter']]
      df_both_ls.append(df)

    df_u = pd.DataFrame(df_both_ls[0])
    df_o = pd.DataFrame(df_both_ls[1])
    df_std = pd.merge(df_u, df_o, on=['poly_lid','poly_cid'], suffixes=('_min','_max'))
    df_std['datetime'] = self.date
    df_std = df_std[['datetime','poly_lid', 'counter_min','counter_max']]

    sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'dashboard', 'fastapi','python'))
    from province_map import output_forli
    df_std = output_forli(df_std)

    pd.options.mode.chained_assignment = None  # default='warn'
    df_min_max = df_std.loc[df_std.counter_min != df_std.counter_max ]
    df_min_max['diff'] = abs(df_min_max.counter_max - df_min_max.counter_min)
    df_min_max['norm'] = abs(df_min_max.counter_max - df_min_max.counter_min)/(df_min_max.counter_max + df_min_max.counter_max)

    mean_norm = df_min_max['norm'].mean()

    df_equal_counter = df_std.loc[df_std.counter_min == df_std.counter_max ]
    df_equal_counter['diff'] = df_equal_counter.counter_min * mean_norm
    df_equal_counter['counter_min'] = round(df_equal_counter.counter_min - df_equal_counter['diff'])
    df_equal_counter['counter_max'] = round(df_equal_counter.counter_max + df_equal_counter['diff'])
    
    df_min_max = df_min_max.drop(columns=['diff','norm'])
    df_equal_counter = df_equal_counter.drop(columns='diff')

    df_std = pd.concat([df_min_max, df_equal_counter])
    df_std = df_std.sort_values(by=['SP'])

    df_std['Indice Variabilità Stagionale'] = df_std[['counter_min', 'counter_max']].apply(lambda x: ' - '.join(x[x.notnull()].map(str)), axis = 1)
    df_std = df_std.drop(columns=['counter_min', 'counter_max', 'datetime'])
    corrected_file = f'{self.unique_file}.corrected.prov.csv'
    df_std.to_csv(corrected_file, sep=';', index=False)

    return corrected_file

  def apply_correction_recursive(self, t, n1, n2, newdelta, polyvisited):
    if abs(newdelta) < self.recursion_threshold: return
    if len(polyvisited) > self.recursion_max_depth: return
    for p, n in self.node_adlist[n2]:
      if p in list(self.poly2coil.keys()): continue
      poly_sit = self.polymap[n1][n2] 
      if n == n1: continue
      if p in polyvisited: continue
      if poly_sit in self.noturn_dict and p in self.noturn_dict[poly_sit] : continue 
      if p in self.patched_list: continue

      newdelta = newdelta * self.we[t][n1][n2][n]
      self.newcnt[t][n2][n] = self.newcnt[t][n2][n] + newdelta
      polyvisited.append(p)
      self.apply_correction_recursive(t, n2, n, newdelta, polyvisited)

  def apply_correction_recursive_backward(self, t, n1, n2, newdelta, polyvisited):
    if abs(newdelta) < self.recursion_threshold: return
    if len(polyvisited) > self.recursion_max_depth: return
    for p, n in self.node_adlist[n1]:
      if p in list(self.poly2coil.keys()): continue
      poly_sit = self.polymap[n1][n2]
      if n == n2: continue
      if p in polyvisited: continue
      if poly_sit in self.noturn_dict and p in self.noturn_dict[poly_sit] : continue
      if p in self.patched_list: continue

      # if p == 401642:
      #   print(f'BACK')
      #   print( f'{n} - > {n1}')
      #   print(f'{newdelta}')
      #   print(f'{self.newcnt[t][n][n1]}')


      newdelta = newdelta * self.web[t][n][n1][n2]
      self.newcnt[t][n][n1] = self.newcnt[t][n][n1] + newdelta

      # if p == 401642:
      #   print(f'{self.newcnt[t][n][n1]}\n')

      polyvisited.append(p)
      self.apply_correction_recursive_backward(t, n, n1, newdelta, polyvisited)

  def compare_plot(self, sel_coil=[]):
    dfb = self.dfb
    dfc = self.dfc
    dfs = self.dfs
    dfu1 = self.dfu1
    coil2poly = self.coil2poly
    poly_adlist = self.poly_adlist
    dir_adlist = self.dir_adlist

    # filter selected coils
    if len(sel_coil) == 0:
      sel_coil = dfb.tag.values
    else:
      sel_coil = sel_coil

    corrected_file = f'{self.unique_file}.corrected'
    dfuc = pd.read_csv(corrected_file, sep=';', parse_dates=True)
    dfuc.oneway = dfuc.oneway.replace('FT', 'IN').replace('TF', 'OUT')
    dfuc['poly_dir'] = [ f'{poly}_{dir}' for poly, dir in dfuc[['poly_cid', 'oneway']].values ]
    dfuc = dfuc.drop(columns=['poly_cid', 'poly_lid', 'oneway']).set_index('poly_dir').T
    dfuc.index = pd.to_datetime(dfuc.index)
    #print(dfuc)

    dfu1 = dfu1[ (dfu1.index >= dfuc.index[0]) & (dfu1.index <= dfuc.index[-1]) ]
    dfc = dfc[ (dfc.index >= dfuc.index[0]) & (dfc.index <= dfuc.index[-1]) ]
    dfs = dfs[ (dfs.index >= dfuc.index[0]) & (dfs.index <= dfuc.index[-1]) ]

    for sc in sel_coil:
      try:
        pcid = coil2poly[sc]
        print(f'Plotting for coil {sc} poly {pcid}')

        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(14, 9))

        blist = [ c for c in dfc.columns if c.startswith(f'{sc}_IN') ]
        for b in blist:
          # print(dfc[b])
          ax1.plot(dfc.index, dfc[b].values, '-o', label=f'{b} - coil data')
          ax1.plot(dfc.index, dfs[b].values, '--', label=f'{b} - simulation')
        ax1.set_title('Barriers comparison')
        ax1.legend()
        ax1.grid(linestyle='--')

        plist = [ c for c in dfu1.columns if c.startswith(f'{pcid}_IN') ]
        for p in plist:
          ax2.plot(dfu1.index, dfu1[p].values, '-', label=f'{p} - original')
          ax2.plot(dfu1.index, dfuc[p].values, '--', label=f'{p} - corrected')
        ax2.set_title('Uniq comparison')
        ax2.legend()
        ax2.grid(linestyle='--')

        if 0:
          ax2r = ax2.twinx()
          # make a plot with different y-axis using second axis object
          for p,b in zip(plist, blist):
            ax2r.plot(dfu1.index, (dfs[b] / dfu1[p]).values, 'og', label=f'synth / uniq ratio')
          ax2r.set_ylabel('Ratio')

        plt.suptitle(f'Correction algorithm comparison for coil {sc} poly cid {pcid}')

        if len(self.global_time_debug):
          outpng = f'{self.unique_file}.corrected-{sc:03d}_debug.png'
        else:
          outpng = f'{self.unique_file}.corrected-{sc:03d}.png'
        print(f'Image saved to : {outpng}')
        plt.savefig(outpng)
        plt.close()

        # nearest poly
        fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(14, 9))
        prop_cycle = plt.rcParams['axes.prop_cycle']
        colors = prop_cycle.by_key()['color']

        # directions
        ptag = f'{pcid}_IN'
        print(sc, pcid, ptag, dir_adlist[ptag])
        for tag, nextcol in zip(dir_adlist[ptag], colors):
          ax1.plot(dfu1.index, dfu1[tag].values, '-', color=nextcol, label=f'{tag} - original')
          ax1.plot(dfu1.index, dfuc[tag].values, '--', color=nextcol, label=f'{tag} - corrected')
        ax1.set_title(f'Direction {ptag}')
        ax1.legend()
        ax1.grid(linestyle='--')

        ptag = f'{pcid}_OUT'
        print(sc, pcid, ptag, dir_adlist[ptag])
        for tag, nextcol in zip(dir_adlist[ptag], colors):
          ax2.plot(dfu1.index, dfu1[tag].values, '-', color=nextcol, label=f'{tag} - original')
          ax2.plot(dfu1.index, dfuc[tag].values, '--', color=nextcol, label=f'{tag} - corrected')
        ax2.set_title(f'Direction {ptag}')
        ax2.legend()
        ax2.grid(linestyle='--')

        plt.suptitle(f'Correction algorithm comparison for coil {sc} poly cid {pcid}, nearest {poly_adlist[pcid]}')

        if len(self.global_time_debug):
          outpng = f'{self.unique_file}.corrected-{sc:03d}_links_debug.png'
        else:
          outpng = f'{self.unique_file}.corrected-{sc:03d}_links.png'
        print(f'Image saved to : {outpng}')
        plt.savefig(outpng)
        plt.close()

      except Exception as e:
        print(f'Error => {e}')


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--sim-basename', help='relative basename to sim', required=True)
  parser.add_argument('-c', '--correct', help='perform correction', action='store_true')
  parser.add_argument('-cf', '--correct_prov', help='perform correction over Forli', action='store_true')
  parser.add_argument('-p', '--plot', help='make plot', action='store_true')
  parser.add_argument('-d', '--debug-times', help='enable debug times', action='store_true')
  parser.add_argument('-cl', '--coil-list', help='list of coil to plot, only with --plot', default=[], nargs='+', type=int)
  args = parser.parse_args()

  config = {
    'coils_table_dir':os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data'),
    # 'noturn_dir':os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra'),
    # 'patch_dir':os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra')
  }
  simc = SimPostCorrection(config, args.sim_basename, args.debug_times)

  if args.correct:
    simc.correct(args.coil_list)

  if args.correct_prov:
    simc.correct_prov(args.coil_list)  

  if args.plot:
    sel_coil_memo = [ 323, 7, 219, 123, 343 ]
    simc.compare_plot(args.coil_list)
