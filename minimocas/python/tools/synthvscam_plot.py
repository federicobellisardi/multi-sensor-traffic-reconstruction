#! /usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime

def synthvscam(camin=None, synin=None, filter='', outpng=''):
  fig, ax = plt.subplots(1,1, figsize=(12,8))

  times = set()
  if camin != '':
    cam_df = pd.read_csv(camin, delimiter=';')
    if filter != []:
      cam_cols = [ c for c in cam_df.columns[2:] if any([ re.match(f, c) != None for f in filter ]) ]
    else:
      cam_cols = [ c for c in cam_df.columns[2:] ]
    #print(cam_cols)
    [ ax.plot(cam_df.timestamp, cam_df[c], '-o', ms=3, lw=1.0, label='DATA ' + c) for c in cam_cols ]
    times.update(cam_df.timestamp)

  if synin != '':
    syn_df = pd.read_csv(synin, delimiter=';')
    if filter != []:
      syn_cols = [ c for c in syn_df.columns[2:] if any([ re.match(f, c) != None for f in filter ]) ]
    else:
      syn_cols = [ c for c in syn_df.columns[2:]  ]
    #print(syn_cols)
    [ ax.plot(syn_df.timestamp, syn_df[c], '--o', ms=3, lw=1.0, label='SIM ' + c) for c in syn_cols ]
    times.update(syn_df.timestamp)

  # downsample x ticks
  times = sorted(list(times))
  times_u = times[::4]
  dates_u = [ datetime.fromtimestamp(t).strftime('%H:%M') for t in times_u ]
  start = datetime.fromtimestamp(min(times)).strftime('%a %d/%m %H:%M%z')
  stop = datetime.fromtimestamp(max(times)).strftime('%a %d/%m %H:%M%z')
  ax.set_xticks(times_u)
  ax.set_xticklabels(dates_u, rotation=45) #, ha='right')
  ax.set_xticks(times, minor=True)

  #plt.title('Simulation vs Data')
  plt.xlabel('Time of day [hh:mm]')
  plt.ylabel('Counter')

  plt.legend(prop={'size': 10})
  plt.tight_layout()
  plt.grid()
  plt.grid(which='minor', linestyle='--')

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  ptitle = f'Comparison of real time data vs simulation for barriers counters.\nPeriod "{start}" - "{stop}"'
  plt.suptitle(ptitle, y=0.98)
  if outpng == '':
    plt.show()
  else:
    plt.savefig(outpng)
  plt.close()

def synthvscam_dir(camin=None, synin=None, filter='', outpng=''):
  max_size=20 #size of legend axis and ticks
  fig, ax = plt.subplots(1,1, figsize=(12,8))
  times = set()
  if camin != '':
    cam_df = pd.read_csv(camin, delimiter=';')
    cam_cols = filter[1]
    ax.plot(cam_df.timestamp, cam_df[cam_cols], '-o', ms=3, lw=1.0, label='DATA ' + cam_cols)
    times.update(cam_df.timestamp)

  if synin != '':
    syn_df = pd.read_csv(synin, delimiter=';')
    syn_cols = filter[0]
    ax.plot(syn_df.timestamp, syn_df[syn_cols], '--o', ms=3, lw=1.0, label='SIM ' + syn_cols)
    times.update(syn_df.timestamp)

  # downsample x ticks
  times = sorted(list(times))
  times_u = times[::4]
  dates_u = [ datetime.fromtimestamp(t).strftime('%H:%M') for t in times_u ]
  start = datetime.fromtimestamp(min(times)).strftime('%a %d/%m %H:%M%z')
  stop = datetime.fromtimestamp(max(times)).strftime('%a %d/%m %H:%M%z')
  ax.set_xticks(times_u)
  ax.set_xticklabels(dates_u, rotation=45) #, ha='right')
  ax.set_xticks(times, minor=True)
  ax.tick_params(axis='x', labelsize=max_size)
  ax.tick_params(axis='y', labelsize=max_size)

  #plt.title('Simulation vs Data')
  plt.xlabel('Time of day [hh:mm]', fontsize=max_size)
  plt.ylabel('Counter', fontsize=max_size)

  plt.legend(prop={'size': 10}, fontsize=max_size)
  plt.tight_layout()
  plt.grid()
  plt.grid(which='minor', linestyle='--')

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  ptitle = f'Comparison of real time data vs simulation for barriers counters.\nPeriod "{start}" - "{stop}"'
  plt.suptitle(ptitle, y=0.98)
  if outpng == '':
    plt.show()
  else:
    plt.savefig(outpng)
  plt.close()

def synthvscam_global(camin=None, synin=None, filter='', dir_map='', outpng=''):
  if filter !='':
     cam_cols = [dir_map[f] for f in filter]
  if dir_map !='':
    syn_cols = filter

  if camin != '':
    cam_df = pd.read_csv(camin, delimiter=';')
    cam_df = cam_df.fillna(0)

  if synin != '':
    syn_df = pd.read_csv(synin, delimiter=';')

  cam_area=[]
  syn_area=[]

  for c, item in enumerate(cam_cols):
    vcam=cam_df[item].to_numpy()
    vsyn=syn_df[syn_cols[c]].to_numpy()
    asyn = vsyn.sum()
    acam = vcam.sum()

    cam_area.append(acam)
    syn_area.append(asyn)


  fig, ax = plt.subplots(1,1, figsize=(12,8))
  ax.plot(cam_area, syn_area, 'o', ms=5)
  global_min = min(min(cam_area),min(syn_area))
  global_max = max(max(cam_area),max(syn_area))
  global_min=0
  ax.plot(np.arange(global_min, global_max), np.arange(global_min, global_max), '--')

  plt.xlabel('Cam area', fontsize=20)
  plt.ylabel('Syn area', fontsize=20)
  start_d = cam_df.datetime.iloc[0].split('+')[0]
  stop_d = cam_df.datetime.iloc[-1].split('+')[0].split(' ')[-1]
  plt.title(f'{start_d}-{stop_d}', fontsize=20)
  plt.savefig(outpng+'.png')

  for i, txt in enumerate(syn_cols):
    ax.annotate(txt, (cam_area[i], syn_area[i]))
  plt.savefig(outpng+'_annotate.png')
  plt.close()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("-ci", "--caminput", help="cam input csv", default='')
  parser.add_argument("-si", "--syninput", help="synthetic input csv", default='')
  parser.add_argument("-f", "--filter", help="list of regexp to filter plot output",  nargs='+', default=[])
  args = parser.parse_args()

  synthvscam(camin=args.caminput, synin=args.syninput, filter=args.filter, outpng='')