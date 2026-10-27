#! /usr/bin/env python3

# Requirements
# LINUX
# sudo apt-get install libgeos-dev libproj-dev
# python3 -m pip install geopandas geoplot

import os
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from shapely import geometry

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  # parser.add_argument('-p', '--doplot', help='enable local plot (requires internet connection and it\'s very slow)', action='store_true')
  # parser.add_argument('-c', '--docoils', help='do coils analysis', action='store_true')
  # parser.add_argument('-s', '--dostreets', help='do streets analysis', action='store_true')
  # parser.add_argument('-g', '--dostreetsgrp', help='do streets groupby analysis', action='store_true')
  parser.add_argument('-c', '--carto', help='cartography polyline geojson', required=True)
  args = parser.parse_args()

  # degree
  polyprofile = '/home/ale/Codice/covid_hep/vars/carto/er-speed.pro'
  base = polyprofile[polyprofile.rfind('/')+1:polyprofile.rfind('.')]
  print(base)

  polypro = pd.read_csv(polyprofile, sep='\s+')
  # print(polypro)
  # print(polypro.columns)
  degreeF = polypro.groupby('node_front_cid').agg({'#poly_cid':'count'}).rename(columns={'#poly_cid':'cnt_poly_F'})
  degreeT = polypro.groupby('node_tail_cid').agg({'#poly_cid':'count'}).rename(columns={'#poly_cid':'cnt_poly_T'})
  degree = degreeF.join(degreeT).fillna(0).astype('int')
  degree['degree'] = degree.cnt_poly_F + degree.cnt_poly_T
  #print(degree)

  # speed
  fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
  axes = axs

  maxbin = polypro['speed'].max()
  st = polypro['speed'].values
  ptype_num = 1
  binwidth = 10 # meters
  hbins = np.arange(30, maxbin + binwidth, binwidth)
  cnt, bins = np.histogram(st, bins=hbins, density=False)
  bins = bins[:-1]
  binw = binwidth / (ptype_num + 1)
  axes.bar(bins + (0 + 0.5)*binw, cnt / len(st), width=binw, label=f'carto {len(st)}')

  axes.set_xticks(bins, minor=True)
  max_tick = 20
  if len(bins) > max_tick:
    bins = bins[::int(len(bins)/max_tick)]
  axes.set_xticks(bins)
  axes.set_xticklabels([ f'{d:.0f}' for d in bins ], rotation=0)
  axes.set_xlabel(f'Speed [km/h]')
  axes.set_ylabel('Fraction')
  axes.set_title(f'Polyline speed distribution')
  #plt.tight_layout()
  axes.grid(which='major', linestyle='-')
  axes.grid(which='minor', linestyle='--')
  axes.set_axisbelow(True)
  axes.legend()

  outfile = f'{base}_speed.png'
  print(outfile)
  plt.savefig(f'{outfile}')
  plt.close()

  # degree
  degreeF = polypro.groupby('node_front_cid').agg({'#poly_cid':'count'}).rename(columns={'#poly_cid':'cnt_poly_F'})
  degreeT = polypro.groupby('node_tail_cid').agg({'#poly_cid':'count'}).rename(columns={'#poly_cid':'cnt_poly_T'})
  degree = degreeF.join(degreeT).fillna(0).astype('int')
  degree['degree'] = degree.cnt_poly_F + degree.cnt_poly_T
  print(degree)

  fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
  axes = axs

  maxbin = degree['degree'].max()
  dt = degree['degree'].values
  mean = degree['degree'].mean()
  ptype_num = 2
  binwidth = 1 # meters
  hbins = np.arange(1, maxbin + binwidth, binwidth)
  cnt, bins = np.histogram(dt, bins=hbins, density=False)
  bins = bins[:-1]
  binw = binwidth / (ptype_num + 1)
  axes.bar(bins + (0 + 0.5)*binw, cnt / len(degree), width=binw, label=f'carto {len(dt)}')

  axes.set_xticks(bins, minor=True)
  max_tick = 20
  if len(bins) > max_tick:
    bins = bins[::int(len(bins)/max_tick)]
  axes.set_xticks(bins)
  axes.set_xticklabels([ f'{d:.0f}' for d in bins ], rotation=0)
  axes.set_xlabel(f'Degree')
  axes.set_ylabel('Fraction')
  axes.set_title(f'Node degree distribution')
  #plt.tight_layout()
  axes.grid(which='major', linestyle='-')
  axes.grid(which='minor', linestyle='--')
  axes.set_axisbelow(True)
  axes.legend()

  outfile = f'{base}_degree.png'
  plt.savefig(f'{outfile}')
  plt.close()

  # length
  poly = gpd.read_file(args.carto)
  poly['length'] = poly.to_crs(epsg=3857).geometry.length
  print(poly)

  sintesifile = '/home/ale/FatOne/Work/Regione/carto_sintesi/reticolo_sintesi.geojson'
  sintesi = gpd.read_file(sintesifile)
  sintesi = sintesi.dropna(subset=['geometry'])
  sintesi['length'] = sintesi.to_crs(epsg=3857).geometry.length
  print(sintesi)
  print(sintesi.columns)

  fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
  axes = axs

  maxbin = poly['length'].max()
  lt = poly['length'].values
  mean = poly['length'].mean()
  binwidth = 5000 # meters
  hbins = np.arange(0, maxbin + binwidth, binwidth)
  cnt, bins = np.histogram(lt, bins=hbins, density=False)

  ptype_num = 2
  bins = bins[:-1]
  binw = binwidth / (ptype_num + 1)
  axes.bar(bins + (0.5)*binw, cnt / len(poly), width=binw, label=f'carto {len(lt)}')

  lt = sintesi['length'].values
  mean = sintesi['length'].mean()
  hbins = np.arange(0, maxbin + binwidth, binwidth)
  cnt, bins = np.histogram(lt, bins=hbins, density=False)
  bins = bins[:-1]
  binw = binwidth / (ptype_num + 1)
  axes.bar(bins + (1 + 0.5)*binw, cnt / len(sintesi), width=binw, label=f'sintesi {len(lt)}')

  #axes.set_yscale('log')
  axes.set_xticks(bins, minor=True)
  max_tick = 20
  if len(bins) > max_tick:
    bins = bins[::int(len(bins)/max_tick)]
  axes.set_xticks(bins)
  axes.set_xticklabels([ f'{d/1000:.0f}' for d in bins ], rotation=0)
  axes.set_xlabel(f'Length [km]')
  axes.set_ylabel('Fraction')
  axes.set_title(f'Polylines length distribution')
  #plt.tight_layout()
  axes.grid(which='major', linestyle='-')
  axes.grid(which='minor', linestyle='--')
  axes.set_axisbelow(True)
  axes.legend()

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  plt.savefig(f'{base}_length.png')
  plt.close()
