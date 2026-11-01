#! /usr/bin/env python3

import numpy as np
import pandas as pd
import argparse
import glob
import os

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-i', '--csvin', help='input coils csv', required=True)
  args = parser.parse_args()

  df = pd.read_csv(args.csvin, sep=';')
  print(df.columns)
  df['datetime'] = pd.to_datetime( [ f'{d}:{i:02d}' for d,i in df[['GIORNO_ORA', 'INTERVALLO']].values ])
  df['day'] = df.datetime.dt.day
  df['quarter_index'] = ( ( df.datetime.dt.hour * 60 + df.datetime.dt.minute ) / 15 ).astype('int')

  df[[
    'day',
    'quarter_index',
    'APPARATO',
    'CORSIA',
    'TIPO_VEICOLO',
    'COUNT(*)'
  ]].to_csv(f'{args.csvin}.readable', sep=';', header=True, index=False)

  grp = df.groupby(['TIPO_VEICOLO']).count()['INTERVALLO'].sort_values()
  print(grp)
