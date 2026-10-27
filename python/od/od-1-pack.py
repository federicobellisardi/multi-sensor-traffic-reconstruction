#! /usr/bin/env python3

import os
#import geopandas as gpd
import numpy as np
import pandas as pd
import argparse
import glob
from datetime import datetime
import matplotlib.pyplot as plt
#import contextily as ctx
#from shapely import geometry
from collections import defaultdict


parser = argparse.ArgumentParser()
parser.add_argument('-t', '--timerange', help='date interval string (short format %%y%%m%%d-%%y%%m%%d)', default='')
parser.add_argument('-d', '--datadir', help='preprocessed data csv folder', required=True)
parser.add_argument('-mo', '--maxo', help='max number of ORIGIN', default=5)
parser.add_argument('-md', '--maxd', help='max number of DESTINATION', default=5)
parser.add_argument('-fo', '--filtero', help='filter data by list of region ORIGIN codes as int (no names)', nargs='+', type=int, default=[])
parser.add_argument('-fd', '--filterd', help='filter data by list of region DESTINATION codes as int (no names)', nargs='+', type=int, default=[])
args = parser.parse_args()

maxo = args.maxo
maxd = args.maxd
shortfmt = '%y%m%d'
midfmt = '%y%m%d%H%M'
tr = args.timerange.split('-')
if len(tr) == 2:
  start = datetime.strptime(tr[0], shortfmt)
  stop = datetime.strptime(tr[1], shortfmt)
  full = False
else:
  start = datetime.now()
  stop = datetime.now()
  full = True
timetag = f'{start.strftime(shortfmt)}-{stop.strftime(shortfmt)}'
print(f'TIME period : full {full}, {start} {stop}')

datafolder = args.datadir
imgfolder = f'{datafolder}_img'
if not os.path.exists(imgfolder): os.mkdir(imgfolder)

datafiles = sorted(glob.glob(f'{datafolder}/*.csv'))
df = pd.DataFrame()
totfiles = 0
procfiles = 0
for dataf in datafiles:
  totfiles += 1
  basedir = dataf[:dataf.rfind('\\')]
  filen = dataf[dataf.rfind('\\')+1:]
  filetime = filen[:filen.rfind('.')]
  filedate = datetime.strptime(filetime, midfmt)

  if start <= filedate < stop or full:
    #print(f'Processing : {dataf}')
    data = pd.read_csv(dataf, sep=';', header=[0, 1], index_col=[0,1,2], parse_dates=True)
    #print(data)
    #print(data.shape)
    df = df.append(data)
    procfiles += 1

df.columns = pd.MultiIndex.from_tuples([ (int(i), j) for i, j in df.columns ])
print(f'FILES parsed {procfiles}/{totfiles}')
df = df.reset_index()
df = df.sort_values(by=['time', 'id_o', 'name_o'])
df['hour'] = [ t.time() for t in df.time ]
print(f'INPUT data {len(df)}')
print(f'{df}')

"""
FILTERS
"""
oin = sorted([ o for o in df.id_o.unique() ])
din = sorted([ d for d in df.columns.get_level_values(0).unique() if isinstance(d, int) ])

tok = datafolder.split('_')[-1]
tago, tagd = tok.split('-')

if tago == 'r':
  filo = [ i for i in args.filtero ]
elif tago == 'rp':
  filo = [ i for i in [ j for j in df.columns.get_level_values(0) if isinstance(j, int) ] if i // 1000 in args.filtero ]
elif tago == 'rpc':
  filo = [ i // 1000000 for i in args.filtero ]

if len(filo) == 0: filo = oin
print(f'FILTER ORIGIN {len(filo)} : {filo}')

if tagd == 'r':
  fild = [ i for i in args.filterd ]
elif tagd == 'rp':
  fild = [ i for i in [ j for j in df.columns.get_level_values(0) if isinstance(j, int) ] if i // 1000 in args.filterd ]
elif tagd == 'rpc':
  fild = [ i // 1000000 for i in args.filterd ]

if len(fild) == 0: fild = din
print(f'FILTER DESTINATION {len(fild)} : {fild}')

df = df[df[('id_o', '')].isin(filo)]
df = df[[ c for c in df.columns if c[0] in fild or isinstance(c[0], str)]]
print(df)

"""
TOTALS aggregation
"""
print(df)
totdf = df.groupby(['id_o', 'name_o']).sum()
#exit(1)
totdf.to_csv(f'{imgfolder}/{datafolder}_{timetag}_od_tot.csv', sep=';', index=True)
#print(totdf)
toto = totdf.sum(axis=0).sort_values(ascending=False)
#print(toto)
totd = totdf.sum(axis=1).sort_values(ascending=False)
#print(totd)
print(f'totdf {totdf.sum().sum()}, toto {toto.sum()}, totd {totd.sum()}')

if 1:
  w, h, d = 15, 10, 70
  plt.figure(figsize=(w, h), dpi=d)

  cnt = totdf.values
  cnt[ cnt == 0 ] = 0.1
  cnt = np.log10(cnt)
  #color_map = plt.imshow(cnt, extent=[0, 1, 0, 1], vmin=0, vmax=10)
  color_map = plt.imshow(cnt.T, extent=[0, 1, 0, 1])
  color_map.set_cmap('plasma')

  ylbl = [ v for v in totdf.columns.get_level_values(1) ]
  ylbl.reverse()
  dy = 1 / len(ylbl)
  plt.gca().set_yticks([ (n + 0.5)*dy for n in range(len(ylbl))])
  plt.gca().set_yticklabels(ylbl)

  xlbl = [ v for v in totdf.index.get_level_values(1) ]
  dx = 1 / len(xlbl)
  plt.gca().set_xticks([ (n + 0.5)*dx for n in range(len(xlbl))])
  plt.gca().set_xticklabels(xlbl, rotation=90)

  plt.colorbar()
  plt.tight_layout()
  plt.xlabel(f'Origin')
  plt.ylabel('Destination')
  plt.tight_layout()
  plt.subplots_adjust(top=0.9)
  plt.suptitle(f'Total occurrences OD matrix ({start} {stop})\nNOTE: log10 colorscale', y=0.98)
  outpng = f'{imgfolder}/{datafolder}_{timetag}_od_tot.png'
  plt.savefig(outpng)
  plt.close()

if 1:
  fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(12, 8))
  axs = axs.flatten()

  ax = axs[0]
  x = range(len(toto))
  xl = toto.index.get_level_values(1)
  vals = toto.values.copy()
  vals[ vals == 0 ] = 0.1
  ax.plot(x, vals, '-o')
  #ax.plot(dfg[d], '-o', label=f'{d[1]} {dfg[d].sum()}')

  ax.set_xticks(x)
  ax.set_xticklabels(xl, rotation=90)
  ax.set_title(f'Total ORIGIN {toto.sum()}')

  ax.set_yscale('log')
  ax.set_xlabel(f'Origin')
  ax.set_ylabel('Counter')
  ax.grid(which='major', linestyle='-')

  ax = axs[1]
  x = range(len(totd))
  xl = totd.index.get_level_values(1)
  vals = totd.values.copy()
  vals[ vals == 0 ] = 0.1
  ax.plot(x, vals, '-o')

  ax.set_xticks(x)
  ax.set_xticklabels(xl, rotation=90)
  ax.set_title(f'Total DESTINATION {totd.sum()}')

  ax.set_yscale('log')
  ax.set_xlabel(f'Destination')
  ax.set_ylabel('Counter')
  ax.grid(which='major', linestyle='-')

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  plt.suptitle(f'Data distribution, period {stop-start} ({start} {stop})', y=0.98)
  outpng = f'{imgfolder}/{datafolder}_{timetag}_tot_od.png'
  plt.savefig(outpng)
  plt.close()

"""
DESTINATION selection
"""
#dsel = [ (di, dn) for di, dn in totd.index if di != 0 ]
dsel = [ (di, dn) for di, dn in totd.index ]
dsel = dsel[:maxd]
print(f'DESTINATION selection {totd.sum()}\n{dsel}')
print(totd.head(maxd))
#print(dsel)

"""
ORIGIN selection
"""
#osel = [ (oi, on) for oi, on in toto.index if oi != 0 ]
osel = [ (oi, on) for oi, on in toto.index ]
osel = osel[:maxo]
print(f'ORIGIN selection {toto.sum()}\n{osel}')
print(toto.head(maxo))
#print(osel)
#exit(1)

"""
TIME AVERAGING (same hour different date)
"""
dfa = df.groupby(['hour', 'id_o', 'name_o']).mean()
tot = totdf.sum().sum()
tota = dfa.sum().sum()
days = (stop - start).days
print(dfa, flush=True)
#dfa = dfa.sort_values(by=['hour', 'id_o', 'name_o'], ascending=[True, True, False])
#dfa = dfa.sort_index(level=['hour', 'id_o', 'name_o'], ascending=[True, True, True])
#dfa = dfa.reset_index(level=['hour', 'id_o', 'name_o'])
dfa = dfa.reset_index()
print(f'tot {tot}, ave {tota}, ratio {tot/tota} = days {days}')
print(dfa, flush=True)
#exit(1)

"""
ORIGIN - time vs local top DEST
"""
for (io, no), dfg in dfa.groupby(['id_o', 'name_o']):
  oidx = (f'{io:03d}', no)
  oidx = (io, no)

  if oidx in osel:
    print('ORIGIN ', oidx)

    sum1 = dfg.sum().iloc[2:].sort_values(ascending=False)
    dselloc = [ (di, dn) for di, dn in sum1.index ] #if di != 0 and dn != no ]
    #dselloc = [ (di, dn) for di, dn in sum1.index if di != 0 and dn != no ]
    dselloc = dselloc[:7]
    #print(sum1, dsel)

    fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
    ax = axs

    ts = [ int(t.timestamp()) for t in dfg.hour ]
    print(ts)
    exit(8)
    tl = [ t.strftime('%H:%M') for t in dfg.hour ]

    for di, dn in dselloc:
      didx = (f'{di:03d}', dn)
      didx = (di, dn)
      #print('dest', didx)
      #print(dfg[didx].shape, dfg[didx].sum())
      ax.plot(ts, dfg[didx], '-o', label=f'{didx[1]} {dfg[didx].sum()}')

    ax.set_xticks(ts)
    ax.set_xticklabels(tl, rotation=45)

    #ax.set_yscale('log')
    ax.legend()
    ax.set_xlabel(f'Time of day [HH:MM]')
    ax.set_ylabel('Counter')
    ax.grid(which='major', linestyle='-')

    plt.tight_layout()
    fig.subplots_adjust(top=0.9)
    plt.suptitle(f'Origin {no} to destinations, average over {stop-start} ({start} {stop})', y=0.98)
    outpng = f'{imgfolder}/{datafolder}_{timetag}_time_o_{no}.png'
    plt.savefig(outpng)
    plt.close()

"""
DEST - time vs local top ORIGIN
"""
for di, dn in dsel:
  print(f'DESTINATION {(di, dn)}')

  dft = dfa[[('hour', ''), ('name_o', ''), (di, dn)]].copy()
  dft = dft.set_index([('hour', ''), ('name_o', '')]).unstack(level=1)
  dft.columns = [ c for c in dft.columns.get_level_values(2) ]

  sum1 = dft.sum().sort_values(ascending=False)
  oselloc = [ on for on in sum1.index if 'altre' not in on and on != dn ]
  oselloc = oselloc[:7]
  #print(sum1, 'oselloc ', oselloc)

  ts = [ int(t.strftime('%s')) for t in dft.index ]
  tl = [ t.strftime('%H:%M') for t in dft.index ]

  fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
  ax = axs
  for no in oselloc:
    ax.plot(ts, dft[no], '-o', label=f'{no} {dft[no].sum()}')

  ax.set_xticks(ts)
  ax.set_xticklabels(tl, rotation=45)
  ax.legend()
  ax.set_xlabel(f'Time of day [HH:MM]')
  ax.set_ylabel('Counter')
  ax.grid(which='major', linestyle='-')

  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  plt.suptitle(f'Destination {dn} from origins, average over {stop-start} ({start} {stop})', y=0.98)
  outpng = f'{imgfolder}/{datafolder}_{timetag}_time_d_{dn.replace("/", "-")}.png'
  plt.savefig(outpng)
  plt.close()

