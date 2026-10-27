#! /usr/bin/env python3

from glob import glob
from enum import Enum
from dateutil import tz
from itertools import product
from tqdm import tqdm_notebook
from pandas.plotting import lag_plot
from datetime import datetime, timedelta
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.graphics.tsaplots import plot_pacf
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

wdclass = {
  'feriali' : [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri' ],
  'festivi' : [ 'Sat', 'Sun' ]
}

wdcat = {
  'Mon' : 'feriali',
  'Tue' : 'feriali',
  'Wed' : 'feriali',
  'Thu' : 'feriali',
  'Fri' : 'feriali',
  'Sat' : 'festivi',
  'Sun' : 'festivi'
}

map_hour = {0: '00', 1: '01', 2: '02', 3: '03', 4: '04',
            5: '05', 6: '06', 7: '07', 8: '08', 9: '09',
            10: '10', 11: '11', 12: '12', 13: '13', 14: '14',
            15: '15', 16: '16', 17: '17', 18: '18', 19: '19',
            20: '20', 21: '21', 22: '22', 23: '23'}

if __name__ == '__main__':
  import argparse
  import matplotlib.pyplot as plt

  def valid_date(s):
    try:
      return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
      msg = "Not a valid date: '{0}'.".format(s)
      raise argparse.ArgumentTypeError(msg)


  def optimize_SARIMA(parameters_list, d, D, m, exog):
    """
    Return dataframe with parameters, corresponding AIC and SSE
    parameters_list - list with (p, q, P, Q) tuples
    d - integration order
    D - seasonal integration order
    m - length of season
    exog - the exogenous variable
    """
    results = []

    for param in tqdm_notebook(parameters_list):
      try:
        model = SARIMAX(exog, order=(param[0], d, param[1]), seasonal_order=(param[2], D, param[3], m)).fit(disp=-1)
      except:
        continue

      aic = model.aic
      results.append([param, aic])

    result_df = pd.DataFrame(results)
    result_df.columns = ['(p,q)x(P,Q)', 'AIC']
    #Sort in ascending order, lower AIC is better
    result_df = result_df.sort_values(by='AIC', ascending=True).reset_index(drop=True)

    return result_df


  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--data', help='counters data csv', required=True)
  parser.add_argument('-pc', '--plotconf', default='')
  parser.add_argument('-tt', '--time_ticks', help='set time spacing between ticks', type=int, default=300)
  parser.add_argument('-tl', '--time_labels', help='set time spacing between ticks\' labels', type=int, default=3600)
  parser.add_argument('-c', '--coil_numbers', help='set coils to analyze', nargs='+', default = None)
  parser.add_argument('-s', '--startdate', help="The Start Date for Sarima Analysis - format YYYY-MM-DD", type=valid_date)
  parser.add_argument('-e', '--enddate', help="The End Date for for Sarima Analysis - format YYYY-MM-DD", type=valid_date)
  parser.add_argument('-from', '--forecast_from', help="The Start Date for Forecasting and to show plot - format YYYY-MM-DD", type=valid_date)
  parser.add_argument('-to', '--forecast_upto', help="The End Date for Forecasting - format YYYY-MM-DD", type=valid_date)
  parser.add_argument('-bp', '--best_param', help="best parameters sarimax df", default=None)
  args = parser.parse_args()

  # inputs and plot ticks manipulations
  filein = args.data

  base_forecast = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_lavoro', 'coil_forecast')
  if not os.path.exists(base_forecast): os.mkdir(base_forecast)

  fine_freq_s = 900

  dt_ticks = args.time_ticks
  if dt_ticks > fine_freq_s:
    tus = dt_ticks // fine_freq_s
  else:
    tus = 1
    dt_ticks = fine_freq_s
  dt_lbls = args.time_labels
  if dt_lbls > dt_ticks:
    lus = dt_lbls // dt_ticks
  else:
    lus = 1
    dt_lbls = dt_ticks
  print(f'Data sampling {fine_freq_s}. Ticks sampling {dt_ticks} u {tus}. Labels sampling {dt_lbls} u {lus}')


  tok = filein[:filein.find('/')].split('_')
  dt_fmt = '%y%m%d-%H%M%S'
  tok[-1] = tok[-1][:tok[-1].find('.')]
  try:
    start = datetime.strptime(tok[-2], dt_fmt)
    stop = datetime.strptime(tok[-1], dt_fmt)
  except:
    start = datetime.strptime(tok[-3], dt_fmt)
    stop = datetime.strptime(tok[-2], dt_fmt)

  # parsing input counters file
  stats = pd.read_csv(filein, header=[0], index_col=[0], sep=';', parse_dates=True)
  stats = stats.interpolate()

  if args.coil_numbers is not None:
    coil_filter = []
    for c in stats.columns:
      for cn in args.coil_numbers:
        if c.startswith(cn):
          coil_filter.append(c)
  else:
    coil_filter = ['282_0', '282_1']

  if args.plotconf != '':
    with open(args.plotconf) as pcin:
      selection = json.load(pcin)
    coil_filter.extend([c for c in selection.keys() if c not in coil_filter ])

  print(f'Filter over coil: {coil_filter}')

  stats = stats[coil_filter]
  '''
  START: Smoother all the data period
  '''
  stats_all = stats.copy()

  ## Uncomment to select a period:
  # if args.forecast_from is not None and args.forecast_upto is not None:
  #   startdate = args.forecast_from
  #   enddate = args.forecast_upto
  #   stats_all['date'] = stats_all.index.date
  #   mask = (stats_all['date'] >= startdate.date()) & (stats_all['date'] <= enddate.date())
  #   stats_all = stats_all.loc[mask]

  stats_all['date'] = stats_all.index.date
  stats_all.index = stats_all.index.time

  # print('\nData not smoothed to compare to forecast:\n', stats_all)

  hrange = pd.date_range("00:00:00", "23:59:59", freq='15min').time

  df = None
  for key, dfg in stats_all.groupby('date'):
    if df is None : df = pd.DataFrame(index=hrange)
    col = [ c for c in dfg.columns if c != 'date']
    for c in col:
      df[(c, key.strftime('%Y-%m-%d'))] = dfg[c]
  stats_all = df

  tnow = datetime.now()
  ave_all = stats_all.copy()
  ave_all = ave_all.stack()
  ave_all.index = pd.MultiIndex.from_tuples([ (t, i[0], i[1]) for t, i in ave_all.index ], names=['time', 'coil', 'date'])

  ave_all = ave_all.reset_index()
  cols_all = ave_all.columns.values
  cols_all[-1] = 'cnt'
  ave_all.columns = cols_all
  ave_all.date = pd.to_datetime(ave_all.date)
  ave_all['wday'] = ave_all.date.dt.strftime('%a')
  smooths_all = {}
  for coilNum, dfg in ave_all.groupby(['coil']):
    dfave_all =  dfg.groupby(['wday', 'time']).mean()
    dfave_all = dfave_all.sort_values(by=['wday', 'time'])
    try:
      dfp_all = dfave_all.unstack(level=0)
      dfp_all.columns = [ v[1] for v in dfp_all.columns ]
      dfp_all = dfp_all[['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']]
      dfp_all['feriali'] = dfp_all[['Mon', 'Tue', 'Wed', 'Thu', 'Fri']].mean(axis=1)
      dfp_all['festivi'] = dfp_all[['Sat', 'Sun']].mean(axis=1)
      dfp_all = dfp_all.astype(int)
      # dfp_all.to_csv(f'{base}/{coilNum}_all.csv', sep=';', index=True)
    except Exception as e:
      print(f'Error with coil  : {e}')

    def box_centered_kernel(tot_len, box_len):
      pad_len = tot_len - box_len
      kern_all = np.concatenate([
      np.zeros((pad_len // 2)),
      np.ones((box_len)) / box_len,
      np.zeros((pad_len - pad_len // 2))# for odd box_len
      ])
      return kern_all
    ma_size = 5 # running average idx interval from time in seconds
    kern_all = box_centered_kernel(len(dfp_all), ma_size)
    smooth_all = pd.DataFrame([], columns=dfp_all.columns, index=dfp_all.index)
    for c in dfp_all.columns:
      conv_all = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dfp_all[c].values ) * np.fft.fft(kern_all) )))
      smooth_all[c] = conv_all
    smooth_all.index.name='time'
    # smooth_all.to_csv(f'{base}/{coilNum}_smooth_all.csv', sep=';', index=True)
    smooths_all[coilNum] = smooth_all
  tave = datetime.now() - tnow
  print(f'Averaging done in {tave} for {smooths_all.keys()}')

  datetime_fmt = '%Y-%m-%d %H:%M:%S'
  for s in smooths_all.keys():
    cols_all = [ c for c in stats_all.columns if c[0] == s ]
    dft_all = stats_all[cols_all].copy()
    dft_all = dft_all.stack()
    dft_all = dft_all.reset_index()
    dft_all.columns = ['time', 'date', 'cnt']
    dft_all['datetime'] = [ datetime.strptime(f'{d[1]} {t}', datetime_fmt) for t, d in dft_all[['time', 'date']].values ]
    dft_all = dft_all.sort_values(by=['datetime'])
    replicas = len(dft_all) // len(smooths_all[s])
    drange_all = pd.date_range(start, stop, freq='1d')
    drange_all = [ d.strftime('%a') for d in drange_all ]
    ave_class_all = [ smooths_all[s][wdcat[d]].values for d in drange_all ]
    ave_day_all = [ smooths_all[s][d].values for d in drange_all ]
    ave_cnt_all = np.concatenate(ave_class_all)
    ave_d_cnt_all = np.concatenate(ave_day_all)
    tidx_all = pd.date_range(start, stop, freq='15min')
    dfave_all = pd.DataFrame(ave_cnt_all, index=tidx_all, columns=['ave_cnt'])
    dfave_all['ave_day_cnt'] = ave_d_cnt_all

    dfs_all = dft_all[['datetime', 'cnt']].set_index('datetime')
    dft_all = dfave_all.merge(dfs_all, left_index=True, right_index=True)
    kern_all = box_centered_kernel(len(dft_all), ma_size)
    dft_all['cnt_smooth'] = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dft_all.cnt ) * np.fft.fft(kern_all) )))

    dft_f_all = dft_all[['cnt_smooth']]

    dft_f_all['date'] = dft_f_all.index.date
    dft_f_all['hour'] = dft_f_all.index.hour
    dft_f_all['map_hour'] = dft_f_all['hour'].map(map_hour)
    dft_f_all = dft_f_all.groupby(['date','map_hour']).sum()

    dft_f_all.index = [str(i)+' '+ str(j) for i,j in zip(dft_f_all.index.get_level_values(0), dft_f_all.index.get_level_values(1))]
    dft_f_all.index = pd.to_datetime(dft_f_all.index, format='%Y-%m-%d %H').strftime('%Y-%m-%d %H:%M:%S')
    dft_f_all.index = pd.to_datetime(dft_f_all.index)
    dft_f_all = dft_f_all.drop(columns='hour')
    # print(f'Data smoothed to compare to forecast, coil {s}:\n', dft_f_all)
    dft_f_all.to_csv(f'{base_forecast}/smoothed_to_compare_s_{s}.csv', sep=';', index=True)

  '''
  END: Smoother all the data period
  '''

  '''
  START:  Building Sarima forecast data smoothed stucture
  '''
  ## Selection of starting and ending period to give to Sarimax:
  if args.startdate is not None and args.enddate is not None:
    startdate = args.startdate
    enddate = args.enddate
    stats['date'] = stats.index.date
    mask = (stats['date'] >= startdate.date()) & (stats['date'] <= enddate.date())
    stats = stats.loc[mask]

  stats['date'] = stats.index.date
  stats.index = stats.index.time

  df = None
  for key, dfg in stats.groupby('date'):
    if df is None : df = pd.DataFrame(index=hrange)
    col = [ c for c in dfg.columns if c != 'date']
    for c in col:
      df[(c, key.strftime('%Y-%m-%d'))] = dfg[c]
  stats = df

  ave = stats.copy()
  ave = ave.stack()
  ave.index = pd.MultiIndex.from_tuples([ (t, i[0], i[1]) for t, i in ave.index ], names=['time', 'coil', 'date'])

  ave = ave.reset_index()
  cols = ave.columns.values
  cols[-1] = 'cnt'
  ave.columns = cols
  ave.date = pd.to_datetime(ave.date)
  ave['wday'] = ave.date.dt.strftime('%a')
  smooths = {}
  for coilNum, dfg in ave.groupby(['coil']):
    dfave =  dfg.groupby(['wday', 'time']).mean()
    dfave = dfave.sort_values(by=['wday', 'time'])
    try:
      dfp = dfave.unstack(level=0)
      dfp.columns = [ v[1] for v in dfp.columns ]
      dfp = dfp[['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']]
      dfp['feriali'] = dfp[['Mon', 'Tue', 'Wed', 'Thu', 'Fri']].mean(axis=1)
      dfp['festivi'] = dfp[['Sat', 'Sun']].mean(axis=1)
      dfp = dfp.astype(int)
    except Exception as e:
      print(f'Error with coil  : {e}')

    def box_centered_kernel(tot_len, box_len):
      pad_len = tot_len - box_len
      kern = np.concatenate([
      np.zeros((pad_len // 2)),
      np.ones((box_len)) / box_len,
      np.zeros((pad_len - pad_len // 2))# for odd box_len
      ])
      return kern
    ma_size = 5 # running average idx interval from time in seconds
    kern = box_centered_kernel(len(dfp), ma_size)
    smooth = pd.DataFrame([], columns=dfp.columns, index=dfp.index)
    for c in dfp.columns:
      conv = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dfp[c].values ) * np.fft.fft(kern) )))
      smooth[c] = conv
    smooth.index.name='time'
    smooths[coilNum] = smooth
  tave = datetime.now() - tnow
  print(f'Averaging done in {tave} for {smooths.keys()}')

  for s in smooths.keys():
    cols = [ c for c in stats.columns if c[0] == s ]
    dft = stats[cols].copy()
    dft = dft.stack()
    dft = dft.reset_index()
    dft.columns = ['time', 'date', 'cnt']
    dft['datetime'] = [ datetime.strptime(f'{d[1]} {t}', datetime_fmt) for t, d in dft[['time', 'date']].values ]
    dft = dft.sort_values(by=['datetime'])
    replicas = len(dft) // len(smooths[s])
    drange = pd.date_range(start, stop, freq='1d') # only for stop = Y M D 00:00:00
    drange = [ d.strftime('%a') for d in drange ]
    ave_class = [ smooths[s][wdcat[d]].values for d in drange ]
    ave_day = [ smooths[s][d].values for d in drange ]
    ave_cnt = np.concatenate(ave_class)
    ave_d_cnt = np.concatenate(ave_day)
    tidx = pd.date_range(start, stop, freq='15min') # only for stop = Y M D 00:00:

    dfave = pd.DataFrame(ave_cnt, index=tidx, columns=['ave_cnt'])
    dfave['ave_day_cnt'] = ave_d_cnt

    dfs = dft[['datetime', 'cnt']].set_index('datetime')
    dft = dfave.merge(dfs, left_index=True, right_index=True)
    kern = box_centered_kernel(len(dft), ma_size)
    dft['cnt_smooth'] = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( dft.cnt ) * np.fft.fft(kern) )))

    print(dft)

    dft_f = dft.copy()
    dft_f = dft_f[['cnt_smooth']]

    dft_f['date'] = dft_f.index.date
    dft_f['hour'] = dft_f.index.hour
    dft_f['map_hour'] = dft_f['hour'].map(map_hour)
    dft_f = dft_f.groupby(['date','map_hour']).sum()

    dft_f.index = [str(i)+' '+ str(j) for i,j in zip(dft_f.index.get_level_values(0), dft_f.index.get_level_values(1))]
    dft_f.index = pd.to_datetime(dft_f.index, format='%Y-%m-%d %H').strftime('%Y-%m-%d %H:%M:%S')
    dft_f.index = pd.to_datetime(dft_f.index)
    dft_f = dft_f.drop(columns='hour')
    print(f'\nData smoothed on which compute forecast, coil {s}\n', dft_f)

    '''
    END: Building Sarima forecast data smoothed stucture
    '''

    fig, ax = plt.subplots(2,1, figsize=(12,8), sharex=True)
    fig.suptitle(f'ACF and PACF')
    sm.graphics.tsa.plot_acf(dft_f['cnt_smooth'], ax=ax[0])
    sm.graphics.tsa.plot_pacf(dft_f['cnt_smooth'], ax=ax[1])
    ax[0].set_ylabel('Autocorrelation')
    ax[1].set_ylabel('Partial Autocorrelation')
    ax[1].set_xlabel('Lag')
    # plt.savefig(f'{base_forecast}/acf_pacf_coil_{s}.png', dpi=150)
    plt.clf()

    ad_fuller_result = adfuller(dft_f['cnt_smooth'])
    print(f'\nADF Statistic: {ad_fuller_result[0]}')
    print(f'p-value: {ad_fuller_result[1]}')

    lag_plot(dft_f)
    # plt.savefig(f'{base_forecast}/lag_plot_coil_{s}.png', dpi=150)
    plt.clf()

    ts = [ t.timestamp() for t in dft_f.index ]
    ts_lbl = [ t.strftime('%b %d') for t in dft_f.index ]
    tick_us = 24

    fig, axes = plt.subplots(1,1, figsize=(12,8), sharex=True)
    axes.set_xlabel('Time')
    axes.set_ylabel('Counter')
    axes.set_title(f'Smoothed plot coil {s}\n{args.startdate.date()} to {args.enddate.date()}', fontweight='bold')
    axes.plot(ts, dft_f['cnt_smooth'], c='blue', label='Observed data')
     # axes.set_xticks(ts, minor=True)
    axes.set_xticks(ts[::tick_us])
    axes.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    axes.grid(which='major', linestyle='-')
    axes.grid(which='minor', linestyle='--')
    axes.legend()
    # plt.savefig(f'{base_forecast}/coil_{s}_from_{args.startdate.date()}_to_{args.enddate.date()}.png', dpi=150)
    plt.clf()

    '''
    Compute Sarima optimization
    '''
    p = range(0, 2, 1)
    d = 1
    q = range(0, 2, 1)
    P = range(0, 2, 1)
    D = 1
    Q = range(0, 2, 1)
    m = 168
    parameters = product(p, q, P, Q)
    parameters_list = list(parameters)
    print(len(parameters_list))

    dateA = str(dft_f.index[0].strftime('%Y%m%d%H%M%S'))
    dateZ = str(dft_f.index[-1].strftime('%Y%m%d%H%M%S'))

    if args.best_param is None:
      ## Find the optimization parameters:
      result_df = optimize_SARIMA(parameters_list, 1, 1, m, dft_f['cnt_smooth'])
      print('\nSarima Optimization\n', result_df)
      result_df.to_csv(f'{base_forecast}/result_df_coil_{s}_m_{m}_{dateA}-{dateZ}.csv', sep=';')
      best_param = result_df['(p,q)x(P,Q)'][0]
    else:
      ## Read the opt parameters from csv
      result_df = pd.read_csv(f'{base_forecast}/result_df_coil_{s}_m_{m}_{dateA}-{dateZ}.csv', sep=';')
      best_param = result_df['(p,q)x(P,Q)'][0]
      best_param = best_param[1:11]
      best_param = tuple(map(int, best_param.split(',')))
    (p_best, q_best, P_best, Q_best) = best_param

    ## Case : m = 168 = 1 week, p,q,P,Q in [0,2] :
    # best_model = SARIMAX(dft_f['cnt_smooth'], order=(1, 1, 1), seasonal_order=(0, 1, 1, m)).fit(dis=-1)

    best_model = SARIMAX(dft_f['cnt_smooth'], order=(p_best, 1, q_best), seasonal_order=(P_best, 1, Q_best, m)).fit(dis=-1)
    print(best_model.summary())

    best_model.plot_diagnostics(figsize=(12,8))
    plt.suptitle(f'Diagnostic Best model')
    plt.savefig(f'{base_forecast}/diagnostic_plot_coil_{s}.png', dpi=150)
    plt.clf()
    '''
    END: Compute Sarima optimization
    '''

    '''
    Plot the predictions of our model and forecast into the future:
    '''
    dft_all = pd.read_csv(f'{base_forecast}/smoothed_to_compare_s_{s}.csv', header=[0], index_col=[0], sep=';', parse_dates=True)
    # print(f'Data smoothed to compare with coil {s}', dft_all)
    start_upto = args.forecast_from.date() + timedelta(days=-1)
    end_obsData = args.enddate.date() + timedelta(days=1)
    end_endto = args.forecast_upto.date() + timedelta(days=-1)

    dft_f_from = dft_f.loc[args.forecast_from.date().strftime('%Y-%m-%d'):end_obsData.strftime('%Y-%m-%d')]
    dft_all_upto = dft_all.loc[end_obsData.strftime('%Y-%m-%d'):end_endto.strftime('%Y-%m-%d')]
    pred_uc = best_model.get_forecast(steps=pd.to_datetime(args.forecast_upto.date().strftime('%Y-%m-%d')))
    pred_ci = pred_uc.conf_int()
    ax = dft_f_from['cnt_smooth'].plot(label='Observed Smoothed Data', c='b', figsize=(12, 8))
    dft_all_upto['cnt_smooth'].plot(label='Observed "Forecasted" Data',c='r', figsize=(12, 8))
    pred_uc.predicted_mean.plot(ax=ax, label='Forecasted Data', c='k', linestyle='--')


    ax.set_xlabel('Date')
    ax.set_ylabel('Counter')
    # ax.set_xticks(ts, minor=True)
    # ax.set_xticks(ts[::tick_us])
    # ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    ax.grid(which='major', linestyle='-')
    ax.grid(which='minor', linestyle='--')
    plt.legend()
    plt.title(f'Forecasted Prediction\ncoil {s} from {args.forecast_from.date()} to {args.forecast_upto.date()}')
    plt.savefig(f'{base_forecast}/forecasted_prediction_coil_{s}_from_{args.forecast_from.date()}_to_{args.forecast_upto.date()}.png', dpi=150)
    plt.clf()

    os.remove(f'{base_forecast}/smoothed_to_compare_s_{s}.csv')
