#! /usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob
import geopandas as gpd
from shapely import geometry

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--detail', help='enable detailed (per coil) plot', action='store_true')
  parser.add_argument('-m', '--dirmap', help='coil direction mapping csv', required=True)
  # parser.add_argument('-o', '--outpng', help='output png', default='')
  args = parser.parse_args()

  # read scan list of parameters
  pdf = pd.read_csv('param_list.csv', sep=';')
  pdf['sim_id'] = [ f'{x:04d}' for x in pdf['sim_id'].values ]
  pdf = pdf.set_index('sim_id')
  #print(pdf)

  # read coil dir mappings
  selcoil = pd.read_csv(args.dirmap, sep=';', comment='#')
  #print(selcoil)
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
  print(f'Selected coils {len(selcoil)}, barriers {len(sel_coildir)}')

  # loop over scan samples and evaluate l2 distance
  dfs = pd.DataFrame(columns=dir_map.values())
  dfs_idx = []
  for sid, params in pdf.iterrows():
    print(f'Collecting data for sim_id {sid}')

    # collect simulation data
    synf = glob.glob(f'{sid}_barriers*.csv')[0] # pretty unsafe
    dfsyn = pd.read_csv(synf, sep=';', parse_dates=['datetime']).set_index('datetime')
    dfsyn = dfsyn[dir_map.values()].sort_index(axis=1).astype(int)
    #print(dfsyn)

    # collect coils data
    coilf = glob.glob(f'{sid}_databarriers*.csv')[0]
    dfcoil = pd.read_csv(coilf, sep=';', parse_dates=['datetime']).drop(columns='timestamp')
    dfcoil.datetime = dfcoil.datetime.dt.tz_convert('Europe/Rome').dt.tz_localize(None)
    dfcoil = dfcoil.set_index('datetime')
    dfcoil = dfcoil[dir_map.keys()]
    dfcoil.columns = [ dir_map[c] for c in dfcoil.columns ]
    dfcoil = dfcoil.sort_index(axis=1).astype(int)

    # sanity checks
    if (dfcoil.columns != dfsyn.columns).all(): raise Exception(f'Synth and coil headers do not match')
    if len(dfcoil) != len(dfsyn): raise Exception(f'Synth and coil lenght do not match')
    #print(dfcoil)

    # detailed per coil plot
    if args.detail:
      if not os.path.exists(sid): os.mkdir(sid)
      for c in coil_list:

        ts = [ t.timestamp() for t in dfsyn.index ]
        ts_lbl = [ t.strftime('%b %d %H:%M') for t in dfsyn.index ]
        tick_us = 8 # axis label every tick_us * 15 min

        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(14, 8))

        ax = axes[0]
        left_c = f'{c}_IN'
        left_coil = dir_map_inv[left_c]
        ax.plot(ts, dfsyn[left_c], '--o', label=f'SIM {left_c}')
        ax.plot(ts, dfcoil[left_c], '-o', label=f'DATA {left_coil}')
        ax.set_xticks(ts, minor=True)
        ax.set_xticks(ts[::tick_us])
        ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='--')
        ax.set_xlabel(f'Time')
        ax.set_ylabel(f'Counter')
        ax.legend()

        ax = axes[1]
        right_c = f'{c}_OUT'
        right_coil = dir_map_inv[right_c]
        ax.plot(ts, dfsyn[right_c], '--o', label=f'SIM {right_c}')
        ax.plot(ts, dfcoil[right_c], '-o', label=f'DATA {right_coil}')
        ax.legend()
        ax.set_xticks(ts, minor=True)
        ax.set_xticks(ts[::tick_us])
        ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='--')
        ax.set_xlabel(f'Time')
        ax.set_ylabel(f'Counter')

        plt.tight_layout()
        fig.subplots_adjust(top=0.9)
        ptitle = f'Scan comparison'
        plt.suptitle(ptitle, y=0.98)
        plt.savefig(f'{sid}/{c}.png')
        plt.close()

    # compute normalized l2 distance
    vsyn = dfsyn.to_numpy()
    vcoil = dfcoil.to_numpy()
    l2 = (vsyn - vcoil)**2
    l2 = pd.DataFrame(l2, index=dfsyn.index, columns=dfsyn.columns).sum()
    l2 /= (vcoil**2).sum(axis=0)
    #print(l2)
    dfs = dfs.append(l2, ignore_index=True)
    dfs_idx.append(sid)

  dfs.index = dfs_idx
  dfs = dfs.T
  #print(dfs)

  # read coils geodata
  barfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
  dfbar = pd.read_csv(barfile, sep=';')
  dfbar = dfbar.drop(columns='Description').set_index('ID')
  geometry = [ geometry.Point(xy) for xy in zip(dfbar.Lon, dfbar.Lat) ]
  crs = 'epsg:4326'
  dfbar = gpd.GeoDataFrame(dfbar, crs=crs, geometry=geometry)
  #print(dfbar)
  coilpro_map = dfbar['PRO'].to_dict()
  #print(coilpro_map)

  # merge info to construct educated axis labels
  dfs[['id', 'dir']] = [ v.split('_') for v in dfs.index ]
  dfs['pro'] = dfs.id.apply(lambda x: coilpro_map[int(x)])
  dfs.index = [ f'{p}_{i}_{d}' for p, i, d in dfs[['pro', 'id', 'dir']].values ]
  dfs = dfs.drop(columns=['pro', 'id', 'dir']).sort_index()
  #print(dfs)

  # scan normalized l2 distance plot
  fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))

  x = range(len(dfs))
  for c in dfs.columns:
    ax.plot(x, dfs[c].values, '-o', label=f'{c} b_RR {pdf.loc[c, "beta-rnd_rnd"]}')

  ax.set_xticks(x)
  ax.set_xticklabels(dfs.index, rotation=45, ha='right')

  ax.legend()
  ax.set_xlabel(f'Coil/Direction tag')
  ax.set_ylabel('Normalized l2 diff')
  ax.grid(which='major', linestyle='-')
  ax.grid(which='minor', linestyle='--')

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  ptitle = f'Scan comparison'
  plt.suptitle(ptitle, y=0.98)
  plt.savefig('scan.png')
  plt.close()
