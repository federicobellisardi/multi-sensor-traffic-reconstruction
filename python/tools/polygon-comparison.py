#! /usr/bin/env python3

import os
import glob
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime

# Dizionari codici provincia e provincia
prov_names = {
  33 : 'PC',
  34 : 'PM',
  35 : 'RE',
  36 : 'MO',
  37 : 'BO',
  38 : 'FE',
  39 : 'RA',
  40 : 'FC',
  99 : 'RN',
}
pro_names = { f'008{pro:03d}' : proname for pro, proname in prov_names.items() }

# Path di Salvataggio dei Plot
my_test_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_lavoro', 'comparison')

# if not os.path.exists(my_test_path): os.mkdir(my_test_path)

def simulation(csvinSim=None, outfile=''):
  df_od = pd.read_csv(csvinSim, header=[0], index_col=[0,1], sep=';', parse_dates=True)
  day_od = df_od.index.get_level_values(0)[0].strftime('%y-%m-%d')
  giorno_od = df_od.index[0][0].strftime('%y%m%d')
  df_od['tot'] = df_od.sum(axis=1)
  df_od = df_od[['tot']]
  df_od = df_od.unstack(level=1)
  df_od.to_csv(my_test_path + '/file_od.csv', sep=';')

  for uselesstag, provcode in df_od.columns:
    ts = [ t.timestamp() for t in df_od.index ]
    ts_lbl = [ t.strftime('%b %d %H:%M') for t in df_od.index ]
    tick_us = 1

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
    ax.set_title('Simulation ' + prov_names[provcode] + '\nDay:' + giorno_od, fontweight='bold')
    ax.plot(ts, df_od[(uselesstag, provcode)].values, '-o', label='Sim Data')
    ax.set_xticks(ts, minor=True)
    ax.set_xticks(ts[::tick_us])
    ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    ax.grid(which='major', linestyle='-')
    ax.grid(which='minor', linestyle='--')
    ax.set_xlabel(f'Time')
    ax.set_ylabel(f'Counter')
    ax.legend()
    fig.savefig(my_test_path + '/' + f'singleprov_{prov_names[provcode]}_{giorno_od}.png')
    plt.clf()
    plt.close()

def dataCompare(csvinSim=None, csvinData=None, outfile=''):
  all_files = sorted(glob.glob(csvinData + '/*.csv'))

  df_od = pd.read_csv(csvinSim, header=[0], index_col=[0,1], sep=';', parse_dates=True)
  day_od = df_od.index.get_level_values(0)[0].strftime('%y-%m-%d')
  giorno_od = df_od.index[0][0].strftime('%y%m%d')
  df_od['tot'] = df_od.sum(axis=1)
  df_od = df_od[['tot']]
  df_od = df_od.unstack(level=1)
  # df_od.to_csv(my_test_path + '/file_od.csv', sep=';')
  df_od.to_csv(outfile + '/file_od.csv', sep=';')
  # df_od = pd.read_csv(my_test_path + '/file_od.csv', header=[0, 1], index_col=[0], sep=';', parse_dates=True)
  df_od = pd.read_csv(outfile + '/file_od.csv', header=[0, 1], index_col=[0], sep=';', parse_dates=True)

  day_od = df_od.index.get_level_values(0).strftime('%y-%m-%d')

  start = df_od.index.min()
  path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_od', 'tables_rpc-rpc')
  stop = df_od.index.max()
  print(f'sim data timespan {start} - {stop} \n')

  df_all = pd.DataFrame()
  li = []

  for csvfile in all_files:
    csvtimestring = os.path.split(csvfile)[-1]
    csvtime = pd.to_datetime(csvtimestring, format='%y%m%d%H%M.csv')
    if csvtime >= start and csvtime <= stop:
      df_csv = pd.read_csv(csvfile, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
      li.append(df_csv)
      df_csv.index = pd.MultiIndex.from_tuples([(i, n) for t, i, n in df_csv.index])
      df_csv = df_csv.T
      date = csvfile[csvfile.rfind('/')+1:csvfile.rfind('.')]
      date = pd.to_datetime(date, format='%y%m%d%H%M%S')

      df_filter = df_csv[df_csv.index.isin([(i, n) for i, n in df_csv.index if i.startswith('008')])]
      df_filter = df_filter.sum(axis=1).to_frame()
      df_filter['prov'] = [i for i in df_filter.index.get_level_values(0).str[:6]]
      df_filter = df_filter.groupby("prov").sum()
      df_filter.columns = [date]
      if len(df_all) == 0:
        df_all = df_filter
      else:
        df_all[date] = df_filter[date]

  df_all = df_all.T
  df_all.columns = pd.Index([pro_names[i] for i in df_all.columns])
  df_od.columns = df_od.columns.droplevel(level=0)
  df_od.columns = pd.Index([prov_names[int(i)] for  i in df_od.columns])

  for provcode in df_od.columns:
    ts = [ t.timestamp() for t in df_od.index ]
    ts_lbl = [ t.strftime('%b %d %H:%M') for t in df_od.index ]
    tick_us = 1

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
    ax.set_xlabel('Time')
    ax.set_ylabel('Counter')
    ax.set_title(f'Simulated Data VS Table Data for {day_od[0]} in {provcode}', fontweight='bold')
    ax.plot(ts, df_od[provcode], '-o', c='blue', label='Simulated Data')
    ax.plot(ts, df_all[provcode], '-o', c='red', label='Table Data')
    ax.set_xticks(ts, minor=True)
    ax.set_xticks(ts[::tick_us])
    ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    ax.grid(which='major', linestyle='-')
    ax.grid(which='minor', linestyle='--')
    ax.set_xlabel(f'Time')
    ax.set_ylabel(f'Counter')
    ax.legend()

    fig.savefig(outfile + f'/SimDataVSDayData_{provcode}_{day_od[0]}.png')
    # fig.savefig(my_test_path + '/' + f'compare_{provcode}_{day_od[0]}.png')
    plt.clf()
    plt.close()

def dataAve(csvinSim=None, csvinAve=None, outfile=''):

  file_od_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_lavoro')

  df_od = pd.read_csv(csvinSim, header=[0], index_col=[0,1], sep=';', parse_dates=True)
  day_od = df_od.index.get_level_values(0)[0].strftime('%y-%m-%d')
  giorno_od = df_od.index[0][0].strftime('%y%m%d')
  df_od['tot'] = df_od.sum(axis=1)
  df_od = df_od[['tot']]
  df_od = df_od.unstack(level=1)
  # df_od.to_csv(file_od_path + '/file_od.csv', sep=';')
  df_od.to_csv(outfile + '/file_od.csv', sep=';')
  # df_od = pd.read_csv(file_od_path + '/file_od.csv', header=[0, 1], index_col=[0], sep=';', parse_dates=True)
  df_od = pd.read_csv(outfile + '/file_od.csv', header=[0, 1], index_col=[0], sep=';', parse_dates=True)

  day_od = df_od.index.get_level_values(0).strftime('%y-%m-%d')
  dayOfWeek = df_od.index.get_level_values(0).weekday.to_list()[0]

  df_od.columns = df_od.columns.droplevel(level=0)
  df_od.columns = pd.Index([prov_names[int(i)] for  i in df_od.columns])

  if dayOfWeek >= 0 and dayOfWeek <=4:
    df_ave = pd.read_csv(csvinAve + '/od-average-weekdays.csv', sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
  else:
    df_ave = pd.read_csv(csvinAve + '/od-average-holidays.csv', sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)

  # df_ave = pd.read_csv(csvinAve, sep=';',header=[0, 1], index_col=[0,1,2], parse_dates=True)
  df_ave.index = pd.MultiIndex.from_tuples([(t, i) for t, i, n in df_ave.index])
  df_ave.index =df_ave.index.droplevel(level=1)
  df_ave = df_ave.groupby(df_ave.index.get_level_values(0)).sum()
  df_ave = df_ave.T
  df_filter = df_ave[df_ave.index.isin([(i, n) for i, n in df_ave.index if i.startswith('008')])]
  df_filter['prov'] = [i for i in df_filter.index.get_level_values(0).str[:6]]
  df_filter = df_filter.groupby("prov").sum()
  df_ave = df_filter.T
  df_ave.columns = pd.Index([pro_names[i] for i in df_ave.columns])

  for provcode in df_ave.columns:
    ts = [ t.timestamp() for t in df_od.index ]
    ts_lbl = [ t.strftime('%b %d %H:%M') for t in df_od.index ]
    tick_us = 1

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
    ax.set_xlabel('Time')
    ax.set_ylabel('Counter')

    if dayOfWeek >= 0 and dayOfWeek <=4:                                                                                # WeekDays
      # weekdays_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_lavoro', 'weekdays')
      # if not os.path.exists(weekdays_path): os.mkdir(weekdays_path)
      ax.set_title(f'AverageData VS DaySimulation in {provcode}_weekdays on {day_od[0]}', fontweight='bold')

    else:                                                                                                               # Holydays
      # holidays_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_lavoro', 'holidays')
      # if not os.path.exists(holidays_path): os.mkdir(holidays_path)
      ax.set_title(f'AverageData VS DaySimulation in {provcode}_holidays on {day_od[0]}', fontweight='bold')

    ax.plot(ts, df_od[provcode], '-o', c='blue', label='Simulated Data')
    ax.plot(ts, df_ave[provcode], '-o', c='red', label='Average Data')
    ax.set_xticks(ts, minor=True)
    ax.set_xticks(ts[::tick_us])
    ax.set_xticklabels(ts_lbl[::tick_us], rotation=45, ha='right')
    ax.grid(which='major', linestyle='-')
    ax.grid(which='minor', linestyle='--')
    ax.set_xlabel(f'Time')
    ax.set_ylabel(f'Counter')
    ax.legend()

    if dayOfWeek >= 5 and dayOfWeek <=6 : fig.savefig(outfile + f'/AverageDataVSDaySim_{provcode}_holidays_{day_od[0]}.png')
    # if dayOfWeek >= 5 and dayOfWeek <=6 : fig.savefig(holidays_path + f'/AverageDataVSDaySim_{provcode}_holidays_{day_od[0]}.png')
    if dayOfWeek >= 0 and dayOfWeek <=4 : fig.savefig(outfile + f'/AverageDataVSDaySim_{provcode}_weekdays_{day_od[0]}.png')
    # if dayOfWeek >= 0 and dayOfWeek <=4 : fig.savefig(weekdays_path + f'/AverageDataVSDaySim_{provcode}_weekdays_{day_od[0]}.png')
    plt.clf()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--csvinSim', help='simulation OD csv file', default=None)
  parser.add_argument('-d', '--csvinData', help='data Tables csv file', default=None)
  parser.add_argument('-av', '--csvinAve', help='averange od csv file', default=None)
  parser.add_argument('-o', '--outfile', help='output filename', default='')
  args = parser.parse_args()

  # Grafici simulazione dei soli dati OD -> -s  ../work_lavoro/od_200212_000000_200212_235959/od_polygon_200212_000000.csv
  if args.csvinSim != None and args.csvinData == None and args.csvinAve == None:
    simulation(csvinSim=args.csvinSim, outfile=args.outfile)

  # Grafici che paragonano i dati della simulazione per quel giorno con i dati tables di quel giorno
  if args.csvinSim != None and args.csvinData != None and args.csvinAve == None:
    dataCompare(csvinSim=args.csvinSim, csvinData=args.csvinData, outfile=args.outfile)  #   -> -s  ../work_lavoro/od_200212_000000_200212_235959/od_polygon_200212_000000.csv
                                                                                         #   -> -d ../work_od/tables_rpc-rpc/

  # Grafici simulazione dati simulazione di quel giorno con la media
  if args.csvinSim != None and args.csvinAve != None and args.csvinData == None:
    dataAve(csvinSim = args.csvinSim, csvinAve=args.csvinAve, outfile=args.outfile)      # -> -s ../work_lavoro/od_200215_000000_200215_235959/od_polygon_200215_000000.csv -av work_lavoro/work_od_average
                                                                                         # -> -s ../work_lavoro/od_200212_000000_200212_235959/od_polygon_200212_000000.csv -av work_lavoro/work_od_average
