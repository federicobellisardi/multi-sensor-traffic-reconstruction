#! /usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob
import numpy as np

def sim_plot_prov(synfile=None, coildata=None, outdir=''):

  # read coils geodata
  barfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
  dfbar = pd.read_csv(barfile, sep=';')
  dfbar = dfbar.drop(columns='Description').set_index('ID')

  # read coil dir mappings
  dirmapfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_spire', 'coils-dir-mapping_template_0.50.csv')

  selcoil = pd.read_csv(dirmapfile, sep=';', comment='#')
  manual_drop_list = [177]
  #print(f'**** NB manually dropped coils : {manual_drop_list}')
  selcoil = selcoil[ ~selcoil.coil_id.isin(manual_drop_list)]

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
  #print(f'Selected coils {len(selcoil)}, barriers {len(sel_coildir)}')

  # load coils data
  dfcoil_all = pd.read_csv(coildata, sep=';', parse_dates=['datetime'])
  dfcoil_all.datetime = dfcoil_all.datetime.dt.tz_convert('Europe/Rome').dt.tz_localize(None)
  #dfcoil_all.datetime = dfcoil_all.datetime.dt.tz_localize(None)
  dfcoil_all = dfcoil_all.set_index('datetime')
  dfcoil_all = dfcoil_all[dir_map.keys()]
  if 1:
    #print(f'**** NB Filling coils data : INTERPOLATION')
    dfcoil_all = dfcoil_all.interpolate()
  else:
    #print(f'**** NB Filling coils data : FILLNA 0')
    dfcoil_all = dfcoil_all.fillna(0)

  dfsyn = pd.read_csv(synfile, sep=';', parse_dates=['datetime']).set_index('datetime')
  dfsyn = dfsyn[dir_map.values()].sort_index(axis=1).astype(int)
  start = dfsyn.index.min()
  stop = dfsyn.index.max() # this must be included
  coil_list = selcoil['coil_id'].to_list()
  coil_IN = [str(c)+'_IN' for c in coil_list]
  coil_OUT = [str(c)+'_OUT' for c in coil_list]
  coil_0 = [str(c)+'_0' for c in coil_list]
  coil_1 = [str(c)+'_1' for c in coil_list]
  coil_list_str = coil_IN + coil_OUT
  coil_list_num = coil_0 + coil_1
  dfsyn = dfsyn[dfsyn.columns.intersection(coil_list_str)]
  #print(dfsyn)

  # collect coils data
  dfcoil = dfcoil_all[ (dfcoil_all.index >= start) & (dfcoil_all.index <= stop) ]
  dfcoil.columns = [ dir_map[c] for c in dfcoil.columns ]
  dfcoil = dfcoil.sort_index(axis=1).astype(int)
  #print(dfcoil)

  list_prov = dfbar.PRO.unique()
  l2_prov = {}
  for p in list_prov:
    coil_p = dfbar[dfbar.PRO == p].index.to_list()
    coil_p_IN = [str(c)+'_IN' for c in coil_p]
    coil_p_OUT = [str(c)+'_OUT' for c in coil_p]
    coil_p = coil_p_IN + coil_p_OUT
    dfsyn_p = dfsyn[dfsyn.columns.intersection(coil_p)].sum(axis=1)
    dfcoil_p = dfcoil[dfcoil.columns.intersection(coil_p)].sum(axis=1)
    ts = [ t.timestamp() for t in dfsyn_p.index ]
    ts_lbl = [ t.strftime('%b %d %H:%M') for t in dfsyn_p.index ]
    tick_us = 8 # axis label every tick_us * 15 min
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(14, 8))
    ax.plot(ts, dfsyn_p, '--o', label=f'SIM {p}')
    ax.plot(ts, dfcoil_p, '-o', label=f'DATA {p}')
    ax.set_xticks(ts, minor=True)
    ax.set_xticks(ts[::tick_us])
    ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    ax.grid(which='major', linestyle='-')
    ax.grid(which='minor', linestyle='--')
    ax.set_xlabel(f'Time')
    ax.set_ylabel(f'Counter')
    ax.legend()
    plt.tight_layout()
    fig.subplots_adjust(top=0.9)
    ptitle = f'Prov {p} scan comparison'
    plt.suptitle(ptitle, y=0.98)
    plt.savefig(f'{outdir}/prov_{p}.png')
    plt.close()

    v0   = dfcoil_p.to_numpy()
    vsyn = dfsyn_p.to_numpy()
    #l2 = (vsyn - v0)**2
    #l2 = l2.sum()
    #l2 /= (v0**2).sum(axis=0)
    #l2_prov[p] = np.sqrt(l2)
    l1 = abs(vsyn - v0)
    l1 = l1.sum()
    l1 /= abs(v0).sum(axis=0)
    l2_prov[p] = l1


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-sd', '--synfile', help='file of synthetic value', required=True)
  parser.add_argument('-cd', '--coildata', help='coils table data file, as produced by coils-model.py', required=True)
  parser.add_argument('-o', '--outdir', help='outdir png', default='')
  args = parser.parse_args()

  sim_plot_prov(synfile=args.synfile, coildata=args.coildata, outdir=args.outdir)

