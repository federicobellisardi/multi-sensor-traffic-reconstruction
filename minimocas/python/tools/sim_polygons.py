#! /usr/bin/env python3

import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def map_polygons(geojson=None, outfile=''):
  try:
    import geopandas as gpd
    import folium

    gdf = gpd.read_file(geojson)
    #print(gdf)
    #print(gdf.columns)

    #gdf = gdf.to_crs(epsg=3857)
    map = folium.Map()
    gdf.apply(lambda row: folium.Polygon(
      locations=[ [lat,lon] for lon,lat in row.geometry.exterior.coords],
      fill_color='blue',
      color='blue',
      popup=folium.Popup(f'<p>id <b>{row.PRO_NAME}</b></br>name <b>{row.PRO}</b></p>', show=True, sticky=True),
    ).add_to(map), axis=1)
    e, s, w, n = gdf.total_bounds
    #print(e, s, w, n)
    map.fit_bounds([ [s,w], [n,e] ])
    map.save(outfile)

  except Exception as e:
    raise Exception(f'You should really install geopandas...anyway here\'s your exception : {e}')

def sim_polygons(csvin=None, outfile=''):
  df = pd.read_csv(csvin, delimiter=';', parse_dates=['timestamp'], index_col='timestamp')
  df = df.pivot(columns='PK_UID').fillna(0)
  #print(df)
  prodict = {
    33 : 'Piacenza',
    34 : 'Parma',
    35 : 'Reggio-Emilia',
    36 : 'Modena',
    37 : 'Bologna',
    38 : 'Ferrara',
    39 : 'Ravenna',
    40 : 'Forlì-Cesena',
    99 : 'Rimini',
  }

  # autoscaling parameters
  maxlbl = 15
  maxtick = maxlbl * 4
  start = df.index[0]
  stop = df.index[-1]
  ts = [ t.timestamp() for t in df.index ]

  # autoscale minor axis ticks
  tsn = len(ts)
  if tsn > maxtick:
    min_us = tsn // maxtick
  else:
    min_us = 1
  minor_ticks = ts[::min_us]
  #print('mnt', len(minor_ticks))

  # autoscale major axis ticks and labels
  if maxtick > maxlbl:
    maj_us = maxtick // maxlbl
  else:
    maj_us = 1
  major_ticks = minor_ticks[::maj_us]

  major_lbl = [ t.strftime('%b %d %H:%M') for t in df.index ]
  major_lbl = major_lbl[::min_us][::maj_us]

  fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 8))
  #axs = axs.flatten()
  axs = [axs]

  axes = axs[0]
  axes.set_xticks(minor_ticks, minor=True)
  axes.set_xticks(major_ticks)
  axes.set_xticklabels(major_lbl, rotation=45)

  for typ, polid in df.columns:
    axes.plot(ts, df[(typ, polid)], '-o', label=f'{prodict[polid]} ({typ})')

  axes.legend()
  axes.set_xlabel(f'Time of day [Month Day HH:MM]')
  axes.set_ylabel('Counter')
  axes.grid(which='major', linestyle='-')
  axes.grid(which='minor', linestyle='--')

  ptitle = f'Population per zone'
  plt.tight_layout()
  fig.subplots_adjust(top=0.9)
  plt.suptitle(ptitle, y=0.98)
  if outfile == '':
    plt.show()
  else:
    plt.savefig(outfile)
  plt.close()

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-g', '--geojson', help='polygons geojson file', default=None)
  parser.add_argument('-c', '--csvin', help='polygons csv file', default=None)
  parser.add_argument('-o', '--outfile', help='output filename', default='')
  args = parser.parse_args()

  if args.csvin != None:
    sim_polygons(csvin=args.csvin, outfile=args.outfile)

  if args.geojson != None:
    map_polygons(geojson=args.geojson, outfile=args.outfile)

