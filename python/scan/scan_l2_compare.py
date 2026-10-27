#! /usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-de', '--detail', help='list coil id for detailed plot', default=[], nargs='+')
  parser.add_argument('-m', '--dirmap', help='coil direction mapping csv', required=True)
  parser.add_argument('-d', '--datadir', help='scan data folder, as produced by scan_par.py', required=True)
  parser.add_argument('-s', '--summary', help='scan summary file', required=True)
  parser.add_argument('-cd', '--coildata', help='coils table data file, as produced by coils-model.py', required=True)
  parser.add_argument('-l2', '--l2plot', help='enalbe l2compare and l2area plot', action='store_true')
  parser.add_argument('-pp', '--provplot', help='enalbe l2compare plot for prov', action='store_true')
  args = parser.parse_args()

  datadir = args.datadir
  summaryfile = args.summary

  # read scan list of parameters
  pdf = pd.read_csv(f'{summaryfile}', sep=';')
  pdf['id'] = [ f'{x:04d}' for x in pdf['id'].values ]
  pdf = pdf.set_index('id')
  #print(pdf)

  # read coil dir mappings
  selcoil = pd.read_csv(args.dirmap, sep=';', comment='#')
  manual_drop_list = [177]
  print(f'**** NB manually dropped coils : {manual_drop_list}')
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
  print(f'Selected coils {len(selcoil)}, barriers {len(sel_coildir)}')

  # load coils data
  coilf = args.coildata
  dfcoil_all = pd.read_csv(coilf, sep=';', parse_dates=['datetime'])
  dfcoil_all.datetime = dfcoil_all.datetime.dt.tz_convert('Europe/Rome').dt.tz_localize(None)
  #dfcoil_all.datetime = dfcoil_all.datetime.dt.tz_localize(None)
  dfcoil_all = dfcoil_all.set_index('datetime')
  dfcoil_all = dfcoil_all[dir_map.keys()]
  if 1:
    print(f'**** NB Filling coils data : INTERPOLATION')
    dfcoil_all = dfcoil_all.interpolate()
  else:
    print(f'**** NB Filling coils data : FILLNA 0')
    dfcoil_all = dfcoil_all.fillna(0)
  #print(dfcoil_all)

  # loop over scan samples and evaluate l2 distance
  dfs = pd.DataFrame(columns=dir_map.values())
  dfs_idx = []
  for sid, params in pdf.iterrows():
    #print(f'Params {params}')

    # collect simulation data
    try:
      synf = glob.glob(f'{datadir}/csv/{sid}_barriers*.csv')[0] # pretty unsafe
    except Exception:
      continue
    #print(f'Collecting data for sim_id {sid}')

    dfsyn = pd.read_csv(synf, sep=';', parse_dates=['datetime']).set_index('datetime')
    dfsyn = dfsyn[dir_map.values()].sort_index(axis=1).astype(int)
    start = dfsyn.index.min()
    stop = dfsyn.index.max() # this must be included
    #print(dfsyn)

    # collect coils data
    dfcoil = dfcoil_all[ (dfcoil_all.index >= start) & (dfcoil_all.index <= stop) ]
    dfcoil.columns = [ dir_map[c] for c in dfcoil.columns ]
    dfcoil = dfcoil.sort_index(axis=1).astype(int)
    #print(dfcoil)

    # sanity checks
    if (dfcoil.columns != dfsyn.columns).all(): raise Exception(f'Synth and coil headers do not match')
    if len(dfcoil) != len(dfsyn): raise Exception(f'Synth and coil lenght do not match')
    #print(dfcoil)

    # read coils geodata
    barfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
    dfbar = pd.read_csv(barfile, sep=';')
    dfbar = dfbar.drop(columns='Description').set_index('ID')
    #print(dfbar)
    coilpro_map = dfbar['PRO'].to_dict()
    #print(coilpro_map)

    # detailed per coil plot
    if len(args.detail):

      if sid in args.detail:
        print(f'Plotting details for sim_id {sid}')
        detaildir = f'{datadir}/details/{sid}'
        if not os.path.exists(detaildir): os.makedirs(detaildir)

        list_prov = dfbar.PRO.unique()
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
          ptitle = f'Simid {sid} Prov {p} scan comparison'
          plt.suptitle(ptitle, y=0.98)
          plt.savefig(f'{detaildir}/{p}.png')
          plt.close()

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
          ptitle = f'Simid {sid} Coil {c} scan comparison @ {params.to_dict()}'
          plt.suptitle(ptitle, y=0.98)
          plt.savefig(f'{detaildir}/{c}.png')
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

  # merge info to construct educated axis labels
  dfs[['id', 'dir']] = [ v.split('_') for v in dfs.index ]
  dfs['pro'] = dfs.id.apply(lambda x: coilpro_map[int(x)])
  dfs.index = [ f'{p}_{i}_{d}' for p, i, d in dfs[['pro', 'id', 'dir']].values ]
  dfs = dfs.drop(columns=['pro', 'id', 'dir']).sort_index()
  #print(dfs)

  # compute best parameters
  dfarea = dfs.sum().to_frame('l2area').sort_values('l2area')
  bestp = dfarea.head(5)
  para_best = pdf.join(bestp, how='right')
  print('And the winners are:\n', para_best)

  # scan normalized l2 distance curve per direction
  if args.l2plot:
    l2dir = f'{datadir}/l2compare'
    if not os.path.exists(l2dir): os.makedirs(l2dir)

    def plot_l2compare(grp_p1, grp_p2, free_p1, free_p2):
      # for instance let
      # grp_p1 = 'ttb'
      # grp_p2 = 'b'
      # free_p1 = 'a_w'
      # free_p2 = 'a_s'
      for (p1, p2), dfg in pdf.groupby([grp_p1, grp_p2]):
        dfs_w = dfs[dfg.index.values]

        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
        x = range(len(dfs_w))
        for c in dfs_w.columns:
          ax.plot(x, dfs_w[c].values, '-o', label=f'{c} {free_p1} {dfg.loc[c, free_p1]} {free_p2} {dfg.loc[c, free_p2]}')
        ax.set_xticks(x)
        ax.set_xticklabels(dfs_w.index, rotation=45, ha='right')
        ax.legend()
        ax.set_xlabel(f'Coil/Direction tag')
        ax.set_ylabel('Normalized l2 diff')
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='--')
        plt.tight_layout()
        fig.subplots_adjust(top=0.9)
        ptitle = f'Scan comparison @ {grp_p1} {p1}, {grp_p2} {p2}'
        plt.suptitle(ptitle, y=0.98)
        plt.savefig(f'{l2dir}/l2comp-{grp_p1}-{p1}-{grp_p2}-{p2}.png')
        plt.close()

    plot_l2compare(grp_p1 = 'ttb', grp_p2 = 'b', free_p1 = 'a_w', free_p2 = 'a_s')
    plot_l2compare(grp_p1 = 'b', grp_p2 = 'a_w', free_p1 = 'a_s', free_p2 = 'ttb')
    plot_l2compare(grp_p1 = 'a_w', grp_p2 = 'a_s', free_p1 = 'ttb', free_p2 = 'b')
    plot_l2compare(grp_p1 = 'a_s', grp_p2 = 'ttb', free_p1 = 'b', free_p2 = 'a_w')

  # scan area plot
  if args.l2plot:
    l2dir = f'{datadir}/l2area'
    if not os.path.exists(l2dir): os.makedirs(l2dir)

    def plot_l2area(grp_p, x_p, curve_p):
      # for instance let
      # grp_p = 'ttb'
      # x_p = 'b'
      # curve_p = 'a_s'
      for p, dfg in pdf.groupby([grp_p]):
        dfs_w = dfs[dfg.index.values]
        dfs_w = dfs_w.sum().to_frame('l2area')
        dfs_w[x_p] = dfg[x_p]
        dfs_w[curve_p] = dfg[curve_p]
        #print(dfs_w)

        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 8))

        ax = axes[0]
        for cp, dftmp in dfg.groupby(curve_p):
          x = dftmp[x_p]
          y = dfs_w.loc[dftmp.index, 'l2area'].values
          ax.plot(x, y, '-o', label=f'{curve_p} {cp}')
        ax.set_xticks(x)
        ax.set_xlabel(f'{x_p}')
        ax.set_ylabel('l2 area')
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='--')
        ax.legend()

        ax = axes[1]
        for cp, dftmp in dfg.groupby(x_p):
          x = dftmp[curve_p]
          y = dfs_w.loc[dftmp.index, 'l2area'].values
          ax.plot(x, y, '-o', label=f'{x_p} {cp}')
        ax.set_xticks(x)
        ax.set_xlabel(f'{curve_p}')
        ax.set_ylabel('l2 area')
        ax.grid(which='major', linestyle='-')
        ax.grid(which='minor', linestyle='--')
        ax.legend()

        plt.tight_layout()
        fig.subplots_adjust(top=0.9)
        ptitle = f'Scan area comparison @ {grp_p} {p}'
        plt.suptitle(ptitle, y=0.98)
        plt.savefig(f'{l2dir}/l2area-{grp_p}-{p}.png')
        plt.close()

    plot_l2area(grp_p = 'ttb', x_p = 'b', curve_p = 'a_s')
    plot_l2area(grp_p = 'b', x_p = 'a_s', curve_p = 'ttb')
    plot_l2area(grp_p = 'a_s', x_p = 'ttb', curve_p = 'b')


