from django.conf import settings

from gui.common import get_colors

import re
import pandas as pd
from glob import glob
from itertools import product
from datetime import datetime, timedelta

import numpy as np

# from tqdm import tqdm_notebook
# from statsmodels.tsa.statespace.sarimax import SARIMAX
# from statsmodels.tsa.holtwinters import ExponentialSmoothing
# import statsmodels

# tune other libs loggers
import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)

##########################
#### MTS DATA WRAPPER ####
##########################
class mts_data():

  def __init__(self):
    # tables file
    self.table_files = glob(f'{settings.DATA_DIR}/coils_table*.csv')
    if len(self.table_files) == 0:
      raise Exception(f'No coils tables files found')

    df = pd.DataFrame()
    for f in self.table_files:
      df = pd.concat((df, pd.read_csv(f, sep=';', parse_dates=True)), axis=0)
    # print(df)  
    df = df.set_index('datetime')
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()
    self.tables = pd.DataFrame(df.values, index=df.index, columns=df.columns) # needed to remove defrag warning
    # print(df)

    # coils geodata
    coils_geodata_file = f'{settings.DATA_DIR}/er_barriers.csv'
    df = pd.read_csv(coils_geodata_file, header=0, names=['ID', 'Lat', 'Lon', 'PRO'], sep=';').astype({
      'ID':'str',
      'Lat':'float',
      'Lon':'float',
      'PRO':'str',
    }).set_index('ID', drop=False)
    self.pro = [ p for p in df.PRO.unique() ]
    self.coilid = sorted([ int(i) for i in df.index ])
    self.coils = df
    # print(df)

    # cluster data
    self.cluster_file = f'{settings.DATA_DIR}/cluster_list.csv'
    self.coils_file = f'{settings.DATA_DIR}/er_barriers.csv'

    # read cluster data
    dfclu = pd.read_csv(self.cluster_file, sep=',', header=0, names=['spira', 'cluster'])
    dfclu[['id', 'dir']] = dfclu.spira.str.split('_', expand=True)
    dfclu = dfclu.astype({'id':'int','dir':'int'})

    # read coil data and merge
    dfcoil = pd.read_csv(self.coils_file, sep=';')
    dfcoil = dfcoil.merge(dfclu, left_on='ID', right_on='id')
    dfcoil = dfcoil[['id', 'dir', 'spira', 'Lat', 'Lon', 'cluster']]

    self.ccluster = dfcoil
    #print(dfcoil)

  def validation(self):
    fmt = '%y%m%d-%H%M%S'
    times = []
    perc_dict_list = []

    for f in self.table_files:
      # print(f)
      start, stop = re.findall(r'.*_(.*)_(.*).csv', f)[0]
      tstart = datetime.strptime(start, fmt)
      tstop = datetime.strptime(stop, fmt)
      times.append([tstart, tstop])
      df_mts = pd.read_csv(f, header=[0], index_col=[0], sep=';', parse_dates=True)
      df_mts['date'] = df_mts.index.date

      for day, df_day in df_mts.groupby('date'):
        df_day = df_day.drop(columns='date')
        # print(day)
        total_values_day = df_day.size
        num_coil_day = 572 * 96
        null_values = df_day.isna().sum().sum()
        perc_null_day = 1 - (null_values / total_values_day)
        perc_null_all = 1 - (null_values / (num_coil_day))
        perc_dict = {day.strftime('%Y-%m-%d') : round(perc_null_all, 2)}
        perc_dict_list.append(perc_dict)

    tmin = min(times, key=lambda x: x[0])[0]
    while tmin.strftime('%a') != 'Mon': tmin -= timedelta(hours=24)
    tmax = max(times, key=lambda x: x[1])[1]
    while tmax.strftime('%a') != 'Sun': tmax += timedelta(hours=24)
    # print(times)

    trange = pd.date_range(start=tmin, end=tmax, freq='1D')
    df = pd.DataFrame(index=trange)
    df['date'] = df.index
    df['day'] = df.index.strftime('%Y-%m-%d')
    df['val'] = 0
    df['week_n'] = df.index.strftime('%Y%V')
    week_to_month = { i : row.date.strftime('%b \'%y') for i, row in df.groupby('week_n').first()[['date']].iterrows() }
    week_to_month['202252'] = "Jan '23"
    df['week_tag'] = df.week_n.map(week_to_month) + df.index.strftime(' - week %V')
    df['weekday'] = df.index.strftime('%a')
    df['weekday_n'] = df.index.strftime('%w')

    for t1, t2 in times:
      for i in perc_dict_list:
        df.loc[ (df.index >= t1) & (df.index < t2), 'val' ] = df['day'].map(i).fillna(df['val'])

    df = df.drop(columns='day')
    two_years_ago = datetime.now() - timedelta(days=2 * 365)
    df = df[df.index >= two_years_ago]

    recs = [
    {
        'date' : f'{row.date.date()}',
        'week' : row.week_tag,
        'weekday' : row.weekday,
        'value' : row.val,
    }  for i, row in df.iterrows() ]

    return recs

  def series(self, coil_id, start_date, stop_date):
    df = self.tables[[f'{coil_id}_0', f'{coil_id}_1']].fillna(0)

    df.index = pd.to_datetime(df.index).tz_localize(None)
    stopdate = pd.to_datetime(stop_date)
    startdate = pd.to_datetime(start_date)
    df = df[(df.index >= startdate) & (df.index <= stopdate)]

    tag0 = f'{coil_id}_0'
    tag1 = f'{coil_id}_1'
    if tag0 in df.columns and tag1 in df.columns:
      records = [
        {
          'date': f'{i}',
          'counter': row[tag0],
          'counter1': row[tag1],
        } for i, row in df.iterrows()
      ]
    else:
      records = []
    return records

  def get_coil_loc(self, coil_id):
    try:
      lat, lon, pro = self.coils.loc[coil_id, ['Lat', 'Lon', 'PRO']].values.tolist()
    except:
      print(f'Coil {coil_id} not in er_barriers')
      lat, lon, pro = None, None, None
    return [lat, lon], pro

  def get_coil_cluster(self):
    dfcoil = self.ccluster

    # prepare colors
    cluster_idx = self.ccluster.cluster.unique()
    cluster_cols = get_colors(len(cluster_idx))
    color_dict = { ci : col for ci, col in zip(cluster_idx, cluster_cols) }
    dfcoil['color'] = dfcoil.cluster.map(color_dict)

    # format for javascript
    dfcoil['text'] = [ f'<svg height="50" width="50" style="position:relative; bottom:25px"> <text x="{5 if d == 0 else 15}" y="25" fill={col} style="font-size:20px">{d}</text> </svg>' for col,d in dfcoil[['color', 'dir']].values ]
    dfcoil['label'] = [ f'coil id {i}' for i in dfcoil['id'].values ]
    data = {}
    for c, dfg in dfcoil.groupby('cluster'):
      data[f'Cluster {c}'] = {
        'color': color_dict[c],
        'data': [ [ [lat, lon], text, lbl ] for  lat,lon,text,lbl in dfg[['Lat', 'Lon', 'text', 'label']].values ]
      }
    geodata = {
      'data': data,
    }

    return geodata

  def get_ranking(self, pro_tag):
    coils = self.coils[ self.coils.PRO == pro_tag ]
    tables = self.tables

    ranking = {}
    for pro, df in coils[['ID', 'PRO']].groupby('PRO'):
      #print(f'Ranking pro : {pro}')
      bar_list = [ f'{i}_0' for i in df.ID.values ]
      bar_list.extend([ f'{i}_1' for i in df.ID.values ])

      dfpro = tables.copy()
      # add missing coils
      for b in bar_list:
        if b not in dfpro.columns:
          dfpro[b] = 0
      dfpro = dfpro[bar_list].sort_index(axis=1)

      dfpro = dfpro.sum().to_frame('tot')
      dfpro['coil_id'] = [ s.split('_')[0] for s in dfpro.index ]
      dfpro = dfpro.groupby('coil_id').sum()
      #print(dfpro)
      dfpro = dfpro.sort_values(by='tot', ascending=False)
      dfpro['cumul'] = dfpro.tot.cumsum() / dfpro.tot.sum()

      # set colors
      bins = [ 0, 0.25, 0.5, 0.75, 1.0 ]
      dfpro['bin'] = pd.cut(dfpro.cumul, bins)
      cbins = dfpro['bin'].unique()
      colors = get_colors(len(cbins), 'Blues')
      colors = get_colors(len(cbins), 'cool')
      colors = get_colors(len(cbins), 'winter')
      colord = { b : c for c,b in zip(colors, cbins) }
      tagd = { b : chr(ord('A') + i) for i,b in enumerate(cbins) }
      dfpro['class_color'] = dfpro.bin.map(colord)
      dfpro['class'] = dfpro.bin.map(tagd)
      dfpro['class_tag'] = [ f'{c} {b}' for c,b in dfpro[['class', 'bin']].values ]
      dfpro['id'] = df.index

      dfpro = dfpro.merge(coils[['Lat', 'Lon']], how='left', left_index=True, right_index=True)
      #print(dfpro)

      ranking[pro] = [
        {
          'coil_id': f'{i}',
          'tot': row.tot,
          'cumul': row.cumul,
          'color': row.class_color,
          'class': row.class_tag,
        } for i, row in dfpro.iterrows()
      ]
      #print(ranking)

      geodata = {}
      for (c, col), dfg in dfpro.groupby(['class', 'class_color']):
        geodata[f'Group {c}'] = {
          'color': col,
          'data': [ [ [lat, lon], f'{cid} {text}', cid ] for  lat,lon,text,cid in dfg[['Lat', 'Lon', 'class_tag', 'id']].values ]
        }

    return ranking[pro_tag], geodata

  # def localanomaly(self, coil_id):

  #   def box_centered_kernel(tot_len, box_len):
  #     pad_len = tot_len - box_len
  #     kern = np.concatenate([
  #     np.zeros((pad_len // 2)),
  #     np.ones((box_len)) / box_len,
  #     np.zeros((pad_len - pad_len // 2))# for odd box_len
  #     ])
  #     return kern

  #   wdclass = {
  #     'feriali' : [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri' ],
  #     'festivi' : [ 'Sat', 'Sun' ]
  #   }

  #   wdcat = {
  #     'Mon' : 'feriali',
  #     'Tue' : 'feriali',
  #     'Wed' : 'feriali',
  #     'Thu' : 'feriali',
  #     'Fri' : 'feriali',
  #     'Sat' : 'festivi',
  #     'Sun' : 'festivi'
  #   }

  #   # congestion status
  #   class cg():
  #     LOW  = 1
  #     AVE  = 2
  #     HIGH = 3

  #   kpi_thresh = {
  #     cg.LOW  : 0.2,
  #     #cg.AVE  : 'gray',
  #     cg.AVE  : 0,
  #     cg.HIGH : 0.8
  #   }

  #   stats = self.tables
  #   stats = stats.interpolate()
  #   stats = stats.fillna(0)

  #   coil_filter = []
  #   for c in stats.columns:
  #     if c.startswith(coil_id):
  #       coil_filter.append(c)

  #   print(f'Filter over coil: {coil_filter}')

  #   stats = stats[coil_filter]

  #   startdate = pd.to_datetime('2022-02-01')
  #   enddate = pd.to_datetime('2022-02-28')
  #   stats['date'] = stats.index.date
  #   mask = (stats['date'] >= startdate.date()) & (stats['date'] <= enddate.date())
  #   stats = stats.loc[mask]

  #   print(stats)

  #   stats['date'] = stats.index.date
  #   stats.index = stats.index.time

  #   df = None
  #   for key, dfg in stats.groupby('date'):
  #     if df is None : df = pd.DataFrame(index=dfg.index)
  #     col = [ c for c in dfg.columns if c != 'date']
  #     for c in col:
  #       df[(c, key.strftime('%Y-%m-%d'))] = dfg[c]
  #   stats = df

  #   tnow = datetime.now()
  #   ave = stats.copy()
  #   ave = ave.stack()
  #   ave.index = pd.MultiIndex.from_tuples([ (t, i[0], i[1]) for t, i in ave.index ], names=['time', 'coil', 'date'])

  #   ave = ave.reset_index()
  #   cols = ave.columns.values
  #   cols[-1] = 'cnt'
  #   ave.columns = cols
  #   ave.date = pd.to_datetime(ave.date)
  #   ave['wday'] = ave.date.dt.strftime('%a')
  #   smooths = {}

  #   for coilNum, dfg in ave.groupby(['coil']):
  #     dfave =  dfg.groupby(['wday', 'time']).mean()
  #     dfave = dfave.sort_values(by=['wday', 'time'])
  #     try:
  #       dfp = dfave.unstack(level=0)
  #       dfp.columns = [ v[1] for v in dfp.columns ]
  #       dfp = dfp[['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']]
  #       dfp['feriali'] = dfp[['Mon', 'Tue', 'Wed', 'Thu', 'Fri']].mean(axis=1)
  #       dfp['festivi'] = dfp[['Sat', 'Sun']].mean(axis=1)
  #       dfp = dfp.astype(int)
  #       dfp.to_csv(f'{settings.DATA_DIR}/{coilNum}.csv', sep=';', index=True)
  #     except Exception as e:
  #       print(f'Error with coil  : {e}')
  #     ma_size = 5 # running average idx interval from time in seconds
  #     kern = box_centered_kernel(len(dfp), ma_size)
  #     smooth = pd.DataFrame([], columns=dfp.columns, index=dfp.index)
  #     for c in dfp.columns:
  #       conv = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dfp[c].values ) * np.fft.fft(kern) )))
  #       smooth[c] = conv
  #     smooth.index.name='time'
  #     smooths[coilNum] = smooth
  #   tave = datetime.now() - tnow
  #   print(f'Averaging done in {tave} for {smooths.keys()}')

  #   datetime_fmt = '%Y-%m-%d %H:%M:%S'
  #   fullt = {}
  #   flustats = {}
  #   for s in smooths.keys():
  #     cols = [ c for c in stats.columns if c[0] == s ]
  #     dft = stats[cols].copy()
  #     dft = dft.stack()
  #     dft = dft.reset_index()
  #     dft.columns = ['time', 'date', 'cnt']
  #     dft['datetime'] = [ datetime.strptime(f'{d[1]} {t}', datetime_fmt) for t, d in dft[['time', 'date']].values ]
  #     dft = dft.sort_values(by=['datetime'])
  #     replicas = len(dft) // len(smooths[s])

  #     stopdate = enddate + timedelta(minutes=1439)
  #     drange = pd.date_range(startdate, enddate, freq='1d') # only for stop = Y M D 00:00:00
  #     drange = [ d.strftime('%a') for d in drange ]
  #     ave_class = [ smooths[s][wdcat[d]].values for d in drange ]
  #     ave_day = [ smooths[s][d].values for d in drange ]
  #     ave_cnt = np.concatenate(ave_class)
  #     ave_d_cnt = np.concatenate(ave_day)
  #     tidx = pd.date_range(startdate, stopdate, freq='15min') # only for stop = Y M D 00:00:

  #     dfave = pd.DataFrame(ave_cnt, index=tidx, columns=['ave_cnt'])
  #     dfave['ave_day_cnt'] = ave_d_cnt

  #     dfs = dft[['datetime', 'cnt']].set_index('datetime')
  #     dft = dfave.merge(dfs, left_index=True, right_index=True)
  #     kern = box_centered_kernel(len(dft), ma_size)
  #     dft['cnt_smooth'] = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dft.cnt ) * np.fft.fft(kern) )))

  #     # l2 diff
  #     l2diff = (dft.cnt - dft.ave_day_cnt)**2
  #     l2d_smooth = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( l2diff ) * np.fft.fft(kern) )))
  #     l2d_ave = l2d_smooth.mean()
  #     l2d_std = l2d_smooth.std()
  #     l2d_thresh = l2d_ave + l2d_std
  #     l2d_cut = l2d_smooth.copy()
  #     l2d_cut[ l2d_cut < l2d_thresh ] = 0
  #     dft['l2_diff'] = l2diff
  #     dft['l2_diff_smooth'] = l2d_smooth
  #     dft['l2_diff_cut'] = l2d_cut

  #     # diff
  #     diff = dft.cnt - dft.ave_day_cnt
  #     diff_smooth = dft.cnt_smooth - dft.ave_day_cnt
  #     l1d_ave = diff_smooth.mean()
  #     l1d_std = diff_smooth.std()

  #     l1d_thresh_up = diff_smooth.quantile(kpi_thresh[cg.HIGH])
  #     l1d_thresh_down = diff_smooth.quantile(kpi_thresh[cg.LOW])

  #     print(f'Coil {s} : LOW {l1d_thresh_down:.2f}({kpi_thresh[cg.LOW]} perc) HIGH {l1d_thresh_up:.2f}({kpi_thresh[cg.HIGH]} perc)')
  #     dft['l1_diff'] = diff
  #     dft['l1_diff_smooth'] = diff_smooth

  #     dft['l1_kpi'] = cg.LOW
  #     dft.loc[ dft.l1_diff_smooth > l1d_thresh_down, 'l1_kpi'] = cg.AVE
  #     dft.loc[ dft.l1_diff_smooth > l1d_thresh_up, 'l1_kpi'] = cg.HIGH

  #     fullt[s] = dft
  #     flustats[s] = {
  #       'l2_ave'      : l2d_ave,
  #       'l2_std'      : l2d_std,
  #       'l2_thr'      : l2d_thresh,
  #       'l1_ave'      : l1d_ave,
  #       'l1_std'      : l1d_std,
  #       'l1_thr_up'   : l1d_thresh_up,
  #       'l1_thr_down' : l1d_thresh_down,
  #     }

  #   return flustats, fullt

# global scope instance of mts wrapper object
mts = mts_data()
