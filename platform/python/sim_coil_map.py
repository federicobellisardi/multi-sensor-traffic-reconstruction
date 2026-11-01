#! /usr/bin/env python3

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob
import numpy as np
import folium

def sim_plot_coils(synfile=None, coildata=None, outdir=''):

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

  #print(dfbar)
  list_name = ['Coil','Lat','Lon','l1','Pro','ra']
  dfl1 = pd.DataFrame(columns=list_name)
  for c in dfcoil.columns:
    v0   = dfcoil[c].to_numpy()
    vsyn = dfsyn[c].to_numpy()
    l1 = abs(vsyn - v0)
    l1 = l1.sum()
    l1 /= abs(v0).sum(axis=0)

    asyn = vsyn.sum()
    a0 = v0.sum()
    ratio = a0/asyn

    num_coil = int(c.split('_')[0])
    lat = dfbar.loc[num_coil  ].Lat
    lon = dfbar.loc[num_coil].Lon
    pro = dfbar.loc[num_coil].PRO
    list_values = [c, lat, lon, l1, pro, ratio]
    dfw = {k:v for k,v in zip(list_name, list_values)}
    dfl1 = dfl1.append(dfw, ignore_index = True)

  dfl1.to_csv(f'{outdir}/metric_score_coils.csv', sep=';', index=False)

  #create a map
  this_map = folium.Map(prefer_canvas=True)
  def plotDot(point):
      '''input: series that contains a numeric named latitude and a numeric named longitude
      this function creates a CircleMarker and adds it to your this_map'''
      if point.l1 < 0.25:
        color_val = 'red'
      elif point.l1 < 0.50:
        color_val = 'green'
      elif point.l1 < 1.0:
        color_val = 'blue'
      else:
        color_val = 'black'
      versus = point.Coil.split('_')[-1]
      if (versus == 'OUT'):
        lon = point.Lon+0.025
      else:
        lon = point.Lon

      folium.CircleMarker(location=[point.Lat, lon],
                          radius=5,
                          fill=True,
                          fillColor = color_val,
                          color=color_val,
                          fillOpacity= 1,
                          weight=1).add_child(folium.Popup(f'{point.Coil} {point.l1:.2f}')).add_to(this_map)

  dfl1.apply(plotDot, axis = 1)
  this_map.fit_bounds(this_map.get_bounds())
  this_map.save(f'{outdir}/coils_map.html')


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-sd', '--synfile', help='file of synthetic value', required=True)
  parser.add_argument('-cd', '--coildata', help='coils table data file, as produced by coils-model.py', required=True)
  parser.add_argument('-o', '--outdir', help='outdir png', default='')
  args = parser.parse_args()

  sim_plot_coils(synfile=args.synfile, coildata=args.coildata, outdir=args.outdir)

