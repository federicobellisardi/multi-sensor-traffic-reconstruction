#! /usr/bin/env python3

# Requirements
# LINUX
# sudo apt-get install libgeos-dev libproj-dev
# python3 -m pip install geopandas geoplot

import os
import geopandas as gpd
import pandas as pd
#import geoplot as gplt
import matplotlib.pyplot as plt
import contextily as ctx
from shapely import geometry

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-p', '--doplot', help='enable local plot (requires internet connection and it\'s very slow)', action='store_true')
parser.add_argument('-c', '--docoils', help='do coils analysis', action='store_true')
parser.add_argument('-s', '--dostreets', help='do streets analysis', action='store_true')
parser.add_argument('-g', '--dostreetsgrp', help='do streets groupby analysis', action='store_true')
parser.add_argument('-o', '--doprov', help='do province analysis', action='store_true')
args = parser.parse_args()

if args.docoils:
  infile = 'MTS_POSTAZIONI_OTT20.shp'
  coils = gpd.read_file(infile)
  coils = coils.to_crs(epsg=3857)
  coils['x'] = coils.geometry.x
  coils['y'] = coils.geometry.y

  coils.ID_Prov = coils.ID_Prov.fillna(-1)
  coils.fid = coils.fid.fillna(-1)

  #print(coils)
  #print(coils.columns)
  #print(coils.crs)
  print(f'Total coils {len(coils)}')

  coilsdf = pd.DataFrame(coils)
  cities = coilsdf.groupby('ID_Prov').count()
  #print(cities)
  fid = coilsdf.groupby('fid').count()
  #print(fid)

  coils_map = 'ER_coils.png'
  if args.doplot:
    ax = coils.plot(alpha=0.5, edgecolor='k', figsize=(12, 12))
    #for idx, row in coils.iterrows(): ax.annotate(s=row['NAME'], xy=row[['x', 'y']], horizontalalignment='center')
    ctx.add_basemap(ax, crs=coils.crs.to_string(), source=ctx.providers.CartoDB.Voyager)
    plt.savefig('ER_coils.png')
    plt.close()

    """
    # showcase online free tile providers (veeeeeery long to execute)
    for pro, sp in ctx.providers.items():
      for mtype in sp.keys():
        outpng = f'ER_coils_{pro}_{mtype}.png'
        try:
          ax = coils.plot(alpha=0.5, edgecolor='k', figsize=(12, 12))
          #for idx, row in coils.iterrows(): ax.annotate(s=row['NAME'], xy=row[['x', 'y']], horizontalalignment='center')
          ctx.add_basemap(ax, crs=coils.crs.to_string(), source=ctx.providers[pro][mtype])
          plt.savefig(outpng)
          print(f'Saved {outpng}')
        except Exception as e:
          print(f'Failed {outpng} : {e}')
        plt.close()
    """

  # for idp in coilsdf['ID_Prov']:
  #   print(idp)

  # filter by bbox
  coils = coils.to_crs(epsg=4326)
  coils['lon'] = coils.geometry.x
  coils['lat'] = coils.geometry.y
  #print(coils)

  coilsbar = pd.DataFrame(coils)
  coilsbar = coilsbar[['NAME', 'lat', 'lon']]
  coilsbar = coilsbar.rename(columns={'NAME':'Description', 'lat':'Lat', 'lon':'Lon'})
  coilsbar['ID'] = coilsbar.Description
  coilsbar = coilsbar[['Description', 'ID', 'Lat', 'Lon']]
  coilsbar = coilsbar.sort_values(by=['Description'])
  coilsbar.to_csv('er_coils_barriers.csv', sep=';', index=False)
  #print(coilsbar)

  # ROIs
  cities_bbox = {
    'BO' : {
      'lat_min' : 44.4202605,
      'lat_max' : 44.554481,
      'lon_min' : 11.2143493,
      'lon_max' : 11.4560485,
    },
    'BO2' : {
      'lat_min' : 44.3347,
      'lat_max' : 44.6589,
      'lon_min' : 10.9582,
      'lon_max' : 11.6819,
    }
  }

  for ct, cv in cities_bbox.items():
    pointList = [
      [ cv['lon_min'], cv['lat_min'] ],
      [ cv['lon_max'], cv['lat_min'] ],
      [ cv['lon_max'], cv['lat_max'] ],
      [ cv['lon_min'], cv['lat_max'] ]
    ]
    poly = geometry.Polygon(pointList)
    spoly = gpd.GeoSeries([poly])
    spoly = spoly.set_crs(epsg=4326)

    subset = coils[coils.within(spoly.geometry.iloc[0])]
    print(f'Coils for {ct} {len(subset)}')
    #print(subset)

    subsetdf = pd.DataFrame(subset)
    subsetdf[['NAME', 'lat', 'lon']].to_csv(f'{ct}_coils.csv', sep=';', index=False)

    if args.doplot:
      subset = subset.to_crs(epsg=3857)
      ax = subset.plot(alpha=0.5, edgecolor='k', figsize=(12, 12))
      for idx, row in subset.iterrows():
        ax.annotate(s=row['NAME'], xy=row[['x', 'y']], horizontalalignment='center')
      ctx.add_basemap(ax, crs=subset.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
      plt.savefig(f'{ct}_coils.png')
      plt.close()

if args.dostreets:
  infile = 'RETICOLO_PRINCIPALE_RER.shp'
  streets = gpd.read_file(infile)
  streets = streets.dropna(subset=['geometry'])
  streets = streets.to_crs(epsg=4326)
  #print(streets)
  #print(streets.columns)
  print(f'Total streets {len(streets)}')
  streets.to_file('er_streets.geojson', driver='GeoJSON')

  if args.doplot:
    ax = streets.plot(alpha=0.5, edgecolor='k', figsize=(12, 12))
    ctx.add_basemap(ax, crs=streets.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
    plt.savefig('er_streets.png')
    plt.close()

  if args.dostreetsgrp:
    streetsdf = pd.DataFrame(streets)
    for c in streetsdf.columns:
      try:
        print(f'\n\n*** Groupby field {c}')
        temp = streetsdf.groupby(c).count()
        print(temp)
      except Exception as e:
        print(f'*** No groupby for {c} : {e}')

  if args.dostreets and args.docoils:
    print(streets)
    print(streets.columns)
    bdsgeo = []
    bdsdata = []
    for city, grp in streets.groupby('Export_O_5'):
      #print(city)
      #print(grp.convex_hull)
      bds = geometry.box(*grp.total_bounds)

      def linestring_to_points(feature,line):
        return [feature, line.coords]
      points = grp.apply(lambda l: linestring_to_points(l['ID_PERC'],l['geometry']),axis=1)
      points = { k : v for k, v in points.values }
      print(points)
      pointlist = []
      totpt = 0
      for k,v in points.items():
        print(k)
        pointlist.extend([ i for i in v ])
        #print(f'points number {len(mp)}')
        #totpt += len(mp)
      print(grp)
      print(len(pointlist), totpt)
      mp = geometry.MultiPoint(pointlist)
      roi = mp.convex_hull
      print(roi)

      #print(bds)
      #bdsgeo.append(bds)
      bdsgeo.append(roi)
      bdsdata.append(city)
      #break

    cityroi = gpd.GeoDataFrame(index=bdsdata, crs=streets.crs, geometry=bdsgeo)
    print(cityroi)

    cicoils = coils.copy()
    cicoils['city'] = ''
    for city, roi in cityroi.iterrows():
      cicoils.loc[cicoils.within(roi.geometry), 'city'] += f'{city}_'
    print(cicoils)

    cicoils[['NAME', 'city', 'lat', 'lon']].to_csv('er_city_coils.csv')

    if args.doplot:
      cityroi = cityroi.to_crs(epsg=3857)
      ax = cityroi.plot(alpha=0.5, edgecolor='k', figsize=(12, 12))
      ctx.add_basemap(ax, crs=cityroi.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
      plt.savefig('er_cityroi.png')
      plt.close()

if args.doprov:
  print('prov')
  proshape = 'Comuni2020-ETRS89-UTM32/V_COM_GPG_Ed_2020.shp'
  prov = gpd.read_file(proshape)
  prov = prov.to_crs(epsg=25832)
  prov['prov'] = prov.ISTAT.str[:3]
  print(prov)
  print(prov.columns)

  if 0:
    for c in prov.columns:
      print(f'Column : {c}')
      try:
        print(prov.groupby(c).count())
      except:
        print(f'error')


