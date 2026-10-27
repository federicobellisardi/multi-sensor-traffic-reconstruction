#! /usr/bin/env python3

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from dateutil import tz

HERE = tz.tzlocal()
UTC = tz.gettz('UTC')

def sim_stats(statsin, outbase='', city='N/A'):
  df = pd.read_csv(statsin, delimiter=';', parse_dates=['event_time'])
  #print(df)

  dfid = df.groupby('id').last()
  dfid['idletime'] = dfid.lifetime - dfid.triptime
  #print(dfid['idletime'])
  #dfid['start_date'] = pd.to_datetime(dfid.start_time, unit='s')
  dfid = dfid.set_index('event_time')
  #dfid = dfid.tz_localize('UTC').tz_convert('Europe/Rome').tz_localize(None)
  start = dfid.index[0]
  stop = dfid.index[-1]
  #print(dfid)

  # compute sub-df for specific analysis
  dfg = dfid[['tag']].resample('300s').count().rename(columns={'tag':'pawn_created'})
  #print(dfg)
  dfin = dfid[ dfid.event_type == 'IN' ].copy()
  dfout = dfid[ dfid.event_type == 'OUT' ].copy()

  tot_pawn = len(dfid)
  tot_pawn_dead = len(dfout)
  tot_pawn_alive = len(dfin)
  tot_check = (tot_pawn == tot_pawn_dead + tot_pawn_alive)

  """
  Dead pawn
  """
  #print(dfout)

  fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(12, 8))
  axs = axs.flatten()

  grp = dfout.groupby('tag')
  ptype_num = len(grp)
  for n, (ptype, dft) in enumerate(grp):
    #print(dft)
    for i, c in enumerate(['triptime']):
      axes = axs[i]

      binwidth = 900 # sec
      maxbin = dfout[c].max() #12 * 3600
      vals = dft[c].values
      hbins = range(0, maxbin + binwidth, binwidth)
      mean = vals.mean()
      cnt, bins = np.histogram(dft[c].values, bins=hbins, density=True)
      bins = bins[:-1]
      binw = binwidth / (ptype_num + 1)
      axes.bar(bins + (n + 0.5)*binw, cnt, width=binw, label=f'{ptype} {len(dft[c])}')
      #axes.set_yscale('log')
      axes.set_xticks(bins, minor=True)
      if len(bins) > 25:
        bins = bins[::4]
      axes.set_xticks(bins)
      axes.set_xticklabels([ timedelta(seconds=int(s)) for s in bins ], rotation=45)
      axes.set_xlabel(f'Time [HH:MM:SS]')
      axes.set_ylabel('Density')
      axes.set_title(f'{c}, mean = {timedelta(seconds=mean)}')
      axes.grid(which='major', linestyle='-')
      axes.grid(which='minor', linestyle='--')
      axes.set_axisbelow(True)
      axes.legend()

    axes = axs[-1]
    maxbin = int(dfout['totdist'].max())
    lt = dft['totdist'].astype(int).values
    mean = dft['totdist'].mean()
    binwidth = 2500 # meters
    hbins = range(0, maxbin + binwidth, binwidth)
    cnt, bins = np.histogram(lt, bins=hbins, density=True)
    bins = bins[:-1]
    binw = binwidth / (ptype_num + 1)
    axes.bar(bins + (n + 0.5)*binw, cnt, width=binw, label=f'{ptype} {len(lt)}')

    #axes.set_yscale('log')
    axes.set_xticks(bins, minor=True)
    max_tick = 20
    if len(bins) > max_tick:
      bins = bins[::int(len(bins)/max_tick)]
    axes.set_xticks(bins)
    axes.set_xticklabels([ f'{d/1000:.2f}' for d in bins ], rotation=45)
    axes.set_xlabel(f'Trip distance [km]')
    axes.set_ylabel('Density')
    axes.set_title(f'covered distance, mean = {mean/1000:.2f}')
    #plt.tight_layout()
    axes.grid(which='major', linestyle='-')
    axes.grid(which='minor', linestyle='--')
    axes.set_axisbelow(True)
    axes.legend()

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  plt.suptitle(f'Pawn stats, city {city}, total created {tot_pawn}, dead {tot_pawn_dead}, alive {tot_pawn_alive}', y=0.98)
  if outbase == '':
    plt.show()
  else:
    plt.savefig(f'{outbase}_hist.png')
  plt.close()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--statsin', help='stats csv input', required=True)
  parser.add_argument('-o', '--outpng', help='output png', default='')
  args = parser.parse_args()

  sim_stats(statsin=args.statsin, outbase=args.outpng)
