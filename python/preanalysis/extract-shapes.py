#! /usr/bin/env python3

import os
import geopandas as gpd
import pandas as pd
import argparse
import glob
from datetime import datetime
import matplotlib.pyplot as plt
import contextily as ctx
from shapely import geometry
import colorsys
from matplotlib.ticker import FuncFormatter

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--basedir', help='basedir to polygons shapefile dataset', required=True)
  parser.add_argument('-t', '--thresh_dist', help='threshold RDP distance in meters', type=int, default=1000)
  # parser.add_argument('-fp', '--prof', help='[params] list of UID of PROVINCE to plot at COMUNE scale (e.g. 008037)', nargs='+', default=['008037'])
  # parser.add_argument('-fc', '--comf', help='[params] list of UID of COMUNI to plot at ACE scale (e.g. 008037006)', nargs='+', default=['008037006'])
  # parser.add_argument('-fa', '--acef', help='[params] list of UID of ACE to plot at ACE scale (e.g. 008037006081)', nargs='+', default=['008037006081'])
  # parser.add_argument('-m', '--domap', help='[params] enable background map', action='store_true')

  args = parser.parse_args()
  base = args.basedir
  rdp_dist = args.thresh_dist
  print(f'Threshold RDP meters : {rdp_dist}')

  """ Plot PRO scale """
  pfile = f'{base}/italy_pro.shp'
  basename = pfile[:pfile.rfind('.')]
  prodf = gpd.read_file(pfile)
  prodf = prodf.to_crs(epsg=3857)

  prodf = prodf[ prodf.REG == 8 ]
  prodf['PK_UID'] = prodf.PRO.astype('int')
  #print(prodf)
  #print(prodf.columns)

  geom_red = []
  for idx, row in prodf.iterrows():
    print(f'PRO : {row.PRO_NAME}')
    if row.geometry.type == 'Polygon':
      polyg = row.geometry.exterior
      print(f'Polygon {len(polyg.coords)}')
    elif row.geometry.type == 'MultiPolygon':
      polyg = row.geometry[0].exterior
      print(f'Multi Polygon {len(polyg.coords)}')
    poly_red = polyg.simplify(rdp_dist)
    print(f'Reduced size {len(poly_red.coords)}')
    poly_red = geometry.Polygon(poly_red)
    geom_red.append(poly_red)

  prodf.geometry = geom_red
  prodf = prodf.to_crs(epsg=4326)
  prodf.to_file(f'er-pro-shapes_{rdp_dist}m.geojson', driver='GeoJSON')
