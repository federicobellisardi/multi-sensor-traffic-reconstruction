#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import argparse
import glob
import json
import os
import sys
from datetime import datetime

try:
  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'bin'))
  from pysim import simulation

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'platform', 'python'))
  from config import config
  from sim_coil_map import sim_plot_coils
  from sim_prov_aggregation import sim_plot_prov

  sys.path.append(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'minimocas', 'python', 'tools'))
  from sim_plot import sim_plot
  from sim_stats import sim_stats
  from sim_wroutes import sim_wroutes
  from sim_polygons import sim_polygons, map_polygons
  from synthvscam_plot import synthvscam

except Exception as e:
  raise Exception(f'library loading error : {e}')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', help='generation json config file', required=True)
  parser.add_argument('-wr', '--without_rnd', help='generation json config file without rnd sources', action ='store_true')
  parser.add_argument('-r', '--run', help='run simulation', action='store_true')
  parser.add_argument('-p', '--doplot', help='make plot', action='store_true')
  args = parser.parse_args()

  with open(args.config, encoding='utf-8') as cin:
    conf = json.load(cin)

  short_fmt = '%y%m%d_%H%M%S'
  date_fmt = '%Y-%m-%d %H:%M:%S'
  polygons_geojson = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-shapes.geojson')
  conf["random"] = args.without_rnd

  cfg = config(conf)
  sched = []
  sched.extend(cfg.schedule_tot())

  for dfsrc, simtemplate in sched:
    # create local reduced version of coils geodata file and counter data
    start = pd.to_datetime(simtemplate['start_date'] + 'CET', format=date_fmt + '%Z')
    stop = pd.to_datetime(simtemplate['stop_date'] + 'CET', format=date_fmt + '%Z')

    timetag = simtemplate['timetag']
    del simtemplate['timetag']
    tag = simtemplate['tag']
    del simtemplate['tag']

    try:
      filter_coils_plot = simtemplate['filter_coils_plot']
      del simtemplate['filter_coils_plot']
    except:
      pass

    try:
      coils_table_file = simtemplate['coils_table_file']
    except:
      pass

    simtemplate['file_polygons'] = polygons_geojson
    simtemplate['enable_polygons'] = True

    simconftag = f'{tag}_{timetag}'
    if not os.path.exists(simconftag): os.mkdir(simconftag)

    dfdump = dfsrc.copy()
    dfdump.insert(loc=0, column='timestamp', value=[ t.timestamp() for t in dfdump.index ])
    camdata = f'{tag}_{timetag}/{tag}_databarriers_{timetag}.csv'
    dfdump.to_csv(camdata, sep=';')

    simconffile = f'{simconftag}/{simconftag}.json'
    with open(simconffile,  'w') as sout:
      json.dump(simtemplate, sout, indent=2)

    # run simulation
    if args.run:
      confs = json.dumps(simtemplate)
      s = simulation(confs)
      print('sim info : {}'.format(s.sim_info()))
      if s.is_valid():
        tsim = datetime.now()
        s.run()
        print(f'Sim done in {datetime.now() - tsim}')

    # plot stuff
    if args.doplot:
      outdir = f'{simconftag}'
      if not os.path.exists(outdir): os.mkdir(outdir)

      try:
        outpng = f'{outdir}/{simconftag}.png'
        sim_plot(confin=simconffile, outpng=outpng, city='ER')
      except Exception as e:
        print(f'Problems with population plot : {e}')

      try:
        sd = start.strftime(short_fmt)
        popf = f'{simconftag}/{tag}_population_{sd}.csv'
        outpng = f'{outdir}/{tag}_population_{sd}.png'
        sim_plot(popin=popf, outpng=outpng, city='ER')
      except Exception as e:
        print(f'Problems with config plot : {e}')

      try:
        synf = f'{simconftag}/{tag}_barriers_{sd}.csv'
        sim_plot_prov(synfile=synf, coildata=camdata, outdir=outdir)
      except Exception as e:
        print(f'Problems with prov plot : {e}')

      try:
        synf = f'{simconftag}/{tag}_barriers_{sd}.csv'
        sim_plot_coils(synfile=synf, coildata=camdata, outdir=outdir)
      except Exception as e:
        print(f'Problems with coil html : {e}')

      try:
        statsf = f'{simconftag}/{tag}_pstats_{sd}.csv'
        outbase = f'{outdir}/{tag}_pstats_{sd}'
        sim_stats(statsin=statsf, outbase=outbase, city='ER')
      except Exception as e:
        print(f'Problems with stats plot : {e}')

      try:
        synf = f'{simconftag}/{tag}_barriers_{sd}.csv'
        outpng = f'{outdir}/{tag}_synthvscam_{sd}.png'
        if len(filter_coils_plot):
          for f in filter_coils_plot:
            synthvscam(camin=camdata, synin=synf, filter=[f], outpng=f'{outdir}/{tag}_synthvscam_{sd}_{f}.png')
        else:
          synthvscam(camin=camdata, synin=synf, filter=filter_coils_plot, outpng=f'{outdir}/{tag}_synthvscam_{sd}.png')
      except Exception as e:
        print(f'Problems with synthvscam plot : {e}')

      try:
        outmap = f'{outdir}/{tag}_polygon_{sd}.html'
        map_polygons(geojson=polygons_geojson, outfile=outmap)
      except Exception as e:
        print(f'Problems with polygons map : {e}')

      try:
        polycsv = f'{simconftag}/{tag}_polygon_{sd}.csv'
        outpng = f'{outdir}/{tag}_polygon_{sd}.png'
        sim_polygons(csvin=polycsv, outfile=outpng)
      except Exception as e:
        print(f'Problems with polygons plot : {e}')
