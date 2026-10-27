import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import argparse
import glob
import os

sns.set()

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-w', '--workdir', help='workdir of input files', required=True)
  parser.add_argument('-nc', '--num_coil', help='id of coil', required=True)
  parser.add_argument('-d', '--date', help='day of analysis in format HHHHMMDD from 20200201 to 20200331', required=True)
  args = parser.parse_args()

  workdir = args.workdir
  plotdir = f'{workdir}/plot'
  date = args.date
  num_coil = args.num_coil

  year  = date[:4]
  month = date[4:6]
  day   = date[6:]

  if (date > '20200331') | (date < '20200201'):
    print('Date Error: Out of Range')
    exit(8)

  if not os.path.exists(plotdir): os.mkdir(plotdir)
  coil_files = glob.glob(f'{workdir}/*.csv')
  coil_files = sorted(coil_files)

  sel_file = 'None'
  for cf in coil_files:
    itime = cf.split('\\')[-1].split('.')[0].split('_')[0]
    if date >= itime:
      sel_file = cf

  df = pd.read_csv(sel_file, sep=';')
  date_format=f'{year}-{month}-{day}'

  ## selection of date
  df = df.loc[df['GIORNO_ORA'].str.startswith(date_format, na=False)].copy()
  ## selection of coil
  df = df[df['APPARATO'] == int(num_coil)]

  num_lane = df['CORSIA'].unique()
  fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 8))
  daylabels = [f'{date_format} {i:02}' for i in np.arange(0,24)]
  xlabels = []
  for i in daylabels:
    for j in np.arange(0,60,15):
      xlabels.append(f'{i}_{j:02}')
  df_full = pd.DataFrame(index=xlabels)
  for nl in num_lane:
    df_lane = df[df['CORSIA'] == nl]
    df_lane = df_lane.groupby(['GIORNO_ORA','INTERVALLO']).sum()['COUNT(*)']
    df_lane_new = pd.DataFrame(df_lane.values, index=[f'{i[0]}_{i[1]:02}' for i in df_lane.index], columns=['COUNT'])
    df_lane_new = df_full.merge(df_lane_new,  right_index=True, left_index=True,how='outer').fillna(0)
    ax.plot(df_lane_new, '-o', label=f'corsia_{nl}')

  ax.legend()
  plt.xticks(xlabels[::4], rotation=45)
  plt.title(f'apparato: {num_coil}, {date}')
  plt.tight_layout()
  plt.savefig(f'{plotdir}/{num_coil}_{date}.png', dpi=150)
  plt.clf()

