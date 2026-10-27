#! /usr/bin/env python3

import os
import argparse
import glob
import pandas as pd
#import geopandas as gpd
from datetime import datetime
import matplotlib.pyplot as plt
#import contextily as ctx
#from shapely import geometry
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dodata', help='parse OD data file', action='store_true')
parser.add_argument('-oa', '--oaggr', help='ORIGIN level of spatial aggregation', choices=['r', 'rp', 'rpc'], default='r')
parser.add_argument('-da', '--daggr', help='DESTINATION level of spatial aggregation', choices=['r', 'rp', 'rpc'], default='r')
args = parser.parse_args()

acedataf = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'ace_geodata.csv')
acedata = pd.read_csv(acedataf, sep=';')
#print(acedata)

idmap = defaultdict(lambda: 'N/A')
idmap.update({ f'{k[0]:03d}' : k[1] for k, _ in acedata.groupby(['REG', 'REG_NAME']) })
idmap.update({ '000' : 'altre regioni' })
idmap.update({ f'{k[0]:03d}{k[1]:03d}' : k[2] for k, _ in acedata.groupby(['REG', 'PRO', 'PRO_NAME']) })
idmap.update({ '000000' : 'altre province' })
idmap.update({ f'{k[0]:09d}' : k[1] for k, _ in acedata.groupby(['RPC', 'COM_NAME']) })
idmap.update({ '000000000' : 'altri comuni' })
#print(len(commap))

tag_o = f'{args.oaggr}_o'
tag_d = f'{args.daggr}_d'

if args.dodata:
  datafolder =  os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'input', 'data_tim', 'ER')
  # datafiles = sorted(glob.glob(f'{datafolder}/*2020*.csv'))
  datafiles = sorted(glob.glob(f'{datafolder}/*.csv'))
  print(f'Data files : {len(datafiles)}')

  uniqrpco = []
  uniqrpcd = []
  timedata = {}
  dfono = pd.DataFrame()
  dfdno = pd.DataFrame()
  dfbno = pd.DataFrame()
  dfgood = pd.DataFrame()
  cnt_ono = 0
  cnt_dno = 0
  cnt_bno = 0
  cnt_tot = 0
  cnt_good = 0
  for i, dataf in enumerate(datafiles):
    #if i > 10: break
    print(f'---\nProcessing {i}/{len(datafiles)}: {dataf}')
    base = dataf[:dataf.rfind('.')]
    df = pd.read_csv(dataf, sep=',', header=[0], dtype={"0": str, "1": str, "2": str, "3": str, "4": int})
    df.columns = ['date', 'min', 'orig', 'dest', 'counter']
    tag_nozone = '000000000000'
    df = df.replace('Altre-zone', tag_nozone)
    cnt_tot += len(df)

    mask = (df.orig == tag_nozone)
    #dfono = dfono.append(df[mask])
    cnt_ono += len(df[mask])

    mask = (df.dest == tag_nozone)
    #dfdno = dfdno.append(df[mask])
    cnt_dno += len(df[mask])

    mask = ((df.orig == tag_nozone) & (df.dest == tag_nozone))
    #dfbno = dfbno.append(df[mask])
    cnt_bno += len(df[mask])

    mask = ((df.orig != tag_nozone) & (df.dest != tag_nozone))
    #dfgood = dfgood.append(df[mask])
    cnt_good += len(df[mask])

    df[['rpc_o', 'sez_o']] = df['orig'].str.split('C', 1, expand=True)
    df[['rpc_d', 'sez_d']] = df['dest'].str.split('C', 1, expand=True)
    df['rp_o'] = df['orig'].str[0:6]
    df['rp_d'] = df['dest'].str[0:6]
    df['r_o'] = df['rpc_o'].str[0:3]
    df['r_d'] = df['rpc_d'].str[0:3]

    dft = df.groupby(['date', 'min']).count()
    if len(dft) != 1:
      raise Exception(f'More than 1 timestamp in file : {dataf}')
    else:
      datet = '{} {}:00'.format(*dft.index[0])
    print(f'Datetime   : {datet}')

    uniqrpco.extend(df[tag_o].unique())
    uniqrpcd.extend(df[tag_d].unique())
    urpco = df[tag_o].unique()
    urpcd = df[tag_d].unique()
    print(f'Unique rpc : o {len(urpco)} d {len(urpcd)}')

    # spatial scale aggregation
    print(f'Aggr type  : {tag_o} {tag_d}')
    rdf = df.groupby([tag_o, tag_d])['counter'].sum()
    rdf = rdf.unstack().fillna(0)

    rdf.index.name = 'id_o'
    rdf.columns.name = 'id_d'
    #print(rdf)
    timedata[datet] = rdf.copy()

  print(f'\nData tot       {cnt_tot}')
  print(f'Data ORIG DEST {cnt_good} ({cnt_good/cnt_tot*100:.1f} %)')
  print(f'Data no ORIG   {cnt_ono} ({cnt_ono/cnt_tot*100:.1f} %)')
  print(f'Data no DEST   {cnt_dno} ({cnt_dno/cnt_tot*100:.1f} %)')
  print(f'Data no BOTH   {cnt_bno} ({cnt_bno/cnt_tot*100:.1f} %)')

  uniqrpco = set(uniqrpco)
  uniqrpcd = set(uniqrpcd)
  print(f'\n*** GLOBAL RESULTS ***')
  print(f'Uniq : o {len(uniqrpco)} d {len(uniqrpcd)}')
  print(f'Timestamp : {len(timedata)}')

  times = sorted(timedata.keys())
  tablefolder = f'tables_{args.oaggr}-{args.daggr}'
  if not os.path.exists(tablefolder): os.mkdir(tablefolder)
  timedf = pd.DataFrame()
  for ts, dft in timedata.items():
    dft = dft.reindex(uniqrpco).fillna(0).reset_index()
    dft['time'] = ts #datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')#pd.to_datetime(ts)
    dft['name_o'] = [ idmap[ido] for ido in dft.id_o ]
    dft = dft.set_index(['time', 'id_o', 'name_o'])
    for rpcd in uniqrpcd:
      if rpcd not in dft.columns:
        dft[rpcd] = 0

    dft.columns = pd.MultiIndex.from_tuples([ (rd, idmap[rd]) for rd in dft.columns ], names=['id_d', 'name_d'])
    start = datetime.strptime(dft.index[0][0], '%Y-%m-%d %H:%M:%S').strftime('%y%m%d%H%M')
    timecsv = f'{tablefolder}/{start}.csv'
    print(f'---\nDumping {timecsv} {dft.shape}')
    dft.to_csv(timecsv, sep=';', index=True)
