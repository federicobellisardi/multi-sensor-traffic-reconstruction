#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

datafile = 'SingoliTransiti-1386674383094.csv'
df = pd.read_csv(datafile, sep=';', engine='c')

df.Data = pd.to_datetime(df.Data, format='%d/%m/%Y %H.%M.%S')
df.Data = df.Data.dt.tz_localize('Europe/Rome')
df = df.set_index('Data', drop=False)

if 0:
  start = pd.to_datetime('2011-05-04 00:00:00 CET')
  stop = pd.to_datetime('2011-05-04 10:10:00 CET')
  stop = pd.to_datetime('2011-05-05 00:00:00 CET')
else:
  start = df.index.min()
  stop = df.index.max()
df = df[ (df.index >= start) & (df.index < stop)]
df['speed_mps'] = df['Velocità'] / 3.6

#[ 'Postazione', 'Data', 'Corsia',
#  'Direzione', 'Descrizione veicolo',
#  'Lunghezza', 'Velocità', 'Headway',
#  'Distanza']
print(df)
print(df.columns)

for cid, dfc in df.groupby('Postazione'):
  print('coil', cid, len(dfc))
  print(dfc.index.min(), dfc.index.max())
  for lane, dfl in dfc.groupby('Corsia'):
    print('lane', lane, len(dfl))
    dfl['dt'] = (dfl.Data - dfl.Data.shift(1)).dt.total_seconds()
    dfl.dt = dfl.dt.shift(-1)
    dfl = dfl.dropna(subset=['dt'])
    dfl = dfl.drop(columns=['Postazione', 'Corsia', 'Direzione', 'Data'])
    dfl['distance'] = dfl['speed_mps'] * dfl.dt
    #print(dfl)

    plot_kwargs = {
      'grid' : True,
      'style' : '-o',
      'figsize' : (12,8),
    }
    dfl.plot(y=['distance', 'Distanza', 'Headway'], **plot_kwargs)
    plt.savefig('distance_compare.png')
    plt.close()

    # dfl['head_diff'] = dfl.Headway - dfl.distance
    # dfl['dist_diff'] = dfl.Distanza - dfl.distance
    # dfl.plot(y=['head_diff', 'dist_diff'], **plot_kwargs)
    # plt.savefig('distance_diff.png')
    # plt.close()
    # dfl = dfl.drop(columns=['head_diff', 'dist_diff'])

    dfl = dfl.drop(columns=['Lunghezza', 'Velocità', 'Headway', 'Distanza'])
    dfl = dfl.reset_index()
    dfl['density'] = 1 / dfl.distance
    #print(dfl)

    # dfl.plot(y=['density'], **plot_kwargs)
    # plt.savefig('distance_density.png')
    # plt.close()

    chunk_size = 500
    mfddata = []
    for t, dfg in dfl.groupby(by=lambda x: x//chunk_size):
      #print(t, '\n', dfg)

      dfg = dfg[ dfg.distance > 0 ] # drop corrupted lines

      ts = dfg.Data.min()
      density = dfg.density.mean()
      density_err = dfg.density.std() / np.sqrt(len(dfg))
      speed = dfg.speed_mps.mean()
      mfddata.append({
        'time'        : ts,
        'density'     : density,
        'density_err' : density_err,
        'speed_mps'   : speed
      })
      #break

    mfd = pd.DataFrame.from_dict(mfddata)
    #print(mfd)

    mfd.plot(x='time', y='density', yerr='density_err', fmt='-o', capsize=4, capthick=1, **plot_kwargs)
    plt.savefig('mfd_data.png')
    plt.close()

    mfd['flux'] = mfd.density * mfd.speed_mps

    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15,8))
    mfd.plot(ax=axes[0], x='density', y='speed_mps', color='blue', kind='scatter', **plot_kwargs)
    mfd.plot(ax=axes[1], x='density', y='flux', color='red', kind='scatter', **plot_kwargs)
    plt.suptitle(f'Coil {cid} lane {lane} chunk_size {chunk_size}\nperiod {start} {stop} ')
    plt.savefig(f'mfd_plot_{cid}_{lane}.png')
    plt.close()

    #break
  #break
