#! /usr/bin/env python3

import os
import pandas as pd
import matplotlib.pyplot as plt

import argparse
parser = argparse.ArgumentParser()
# parser.add_argument('-p', '--doplot', help='enable local plot (requires internet connection and it\'s very slow)', action='store_true')
# parser.add_argument('-c', '--docoils', help='do coils analysis', action='store_true')
# parser.add_argument('-s', '--dostreets', help='do streets analysis', action='store_true')
# parser.add_argument('-g', '--dostreetsgrp', help='do streets groupby analysis', action='store_true')
# parser.add_argument('-o', '--doprov', help='do province analysis', action='store_true')
args = parser.parse_args()

datafile = 'Viasat/EMILIA_DEMO.csv'
cpfile = datafile[:datafile.rfind('.')]
cpfile = f'{cpfile}.cpcsv'

df = pd.read_csv(datafile, sep=';', decimal=',', parse_dates={'datetime':[2]}, engine='c') #, nrows=500000)
df.datetime = df.datetime.dt.tz_localize('Europe/Rome')
print(df)
print(df.columns)
print(df.dtypes)

dfout = df[['DEVICE_ID', 'datetime', 'GPS_LAT', 'GPS_LON', 'GPS_SPEED', 'GPS_DIR', 'GPS_HDOP', 'VEHICLE_TYPE']]
dfout = dfout.rename(columns={
  'DEVICE_ID': 'id', 
  'GPS_LAT': 'lat', 
  'GPS_LON': 'lon', 
  'GPS_SPEED': 'speed', 
  'GPS_DIR': 'direction', 
  'GPS_HDOP': 'hdop',
  'VEHICLE_TYPE': 'type'
})
#dfout.type = [ 'private' if v == 1 else 'commercial' for v in dfout.type.values ]
#dfout.datetime = pd.to_datetime(dfout.datetime)
dfout['timestamp'] = (dfout.datetime.astype('int') * 1e-9).astype('int') #[ t.timestamp() for t in dfout.datetime.values ]
print(dfout)
dfout[[
  'id',
  'timestamp',
  'lat',
  'lon',
  'speed',
  'hdop',
  'type'
]].to_csv(cpfile, sep=';', index=False)
# grp = df.groupby('VEHICLE_TYPE').count()
# print(grp)
