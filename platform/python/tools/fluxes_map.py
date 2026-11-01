#! /usr/bin/env python3

import numpy as np
import pandas as pd
import geopandas as gpd
import argparse
import os
import folium
from folium.plugins import BeautifyIcon
from matplotlib import cm
from matplotlib.colors import to_hex, rgb2hex

def fluxes_map(uniq_file, carto_file):
  cnt = pd.read_csv(uniq_file, sep=';')
  cnt = cnt.drop('poly_lid', axis=1)
  cnt = cnt.groupby('poly_cid').sum()
  ctnT = cnt.T
  ctnT.index = pd.to_datetime(ctnT.index)
  ctnT = ctnT.groupby([pd.Grouper(freq = '1H')]).sum()
  cnt = ctnT.T

  cnt['uniq_cnt'] = cnt.sum(axis=1)
  cnt['mean_cnt'] = cnt.mean(axis=1).round(0)
  cnt.uniq_cnt.fillna(0, inplace=True)
  cnt.drop(cnt.columns.difference(['uniq_cnt','mean_cnt']), 1, inplace=True)

  import matplotlib.pyplot as plt
  fig, ax = plt.subplots()
  cnt[['uniq_cnt']].hist(ax=ax, bins=70, rwidth=0.8)

  quantiles_val = [0.0, 0.20, 0.40, 0.60, 0.80, 0.90, 1.0]
  quantiles = cnt.uniq_cnt.quantile(quantiles_val).to_list()
  bins = [int(q) for q in quantiles]
  cmap = cm.get_cmap('viridis', len(bins)-1)
  rgb_scale = cmap(quantiles_val)
  color_scale = [rgb2hex(r) for r in rgb_scale]
  color_scale = color_scale[:-1]
  default_color = color_scale[1]
  map_col_quantil={}
  for i in np.arange(0, len(color_scale)):
    label = f'{quantiles_val[i]} < q <= {quantiles_val[i+1]}'
    map_col_quantil[color_scale[i]]=label
  ax.set_yscale('log')

  cartofile =  os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'carto.geojson')
  # cartofile =  os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-carto.geojson')
  if carto_file == None:
    try:
      carto = gpd.read_file(cartofile)
    except Exception as e:
      print('Carto not found: ', e)
  else:
    carto = gpd.read_file(carto_file)

  # carto = carto[~carto.poly_cid.isin(cnt.index)]

  list_color = pd.cut(cnt.uniq_cnt, bins=bins, labels=color_scale)
  carto['color'] = list_color.to_list()
  carto.color.fillna(default_color, inplace=True)
  carto['quantile'] = [map_col_quantil[i] for i in carto.color]
  carto['cnt'] = cnt.uniq_cnt.to_list()
  carto['media'] = cnt.mean_cnt.to_list()

  # Create Table Data to send
  tab_data = False
  if tab_data:
    carto_tab = carto.copy()
    carto_tab.index = carto.poly_cid
    carto_tab = carto_tab.drop(columns=['color', 'poly_lid','poly_cid', 'geometry', 'poly_nF','poly_length','poly_nT'])
    filein = uniq_file
    tok = filein.split('/')[-1].split('.')[0]
    ws= os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_ws', 'output')
    if not os.path.exists(ws): os.mkdir(ws)
    carto_tab.to_csv(f'{ws}/{tok}_tab_data.csv')

  # layers
  center = carto.to_crs(epsg=3003).centroid.to_crs(epsg=4326)
  center = [ center.y.mean(), center.x.mean() ]

  # sort for color (for ordered visualization)
  carto.sort_values(by='quantile', inplace=True)

  m = folium.Map(location=center, control_scale=True)
  import warnings
  warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)

  layerlabel = '<span style="color: {col};">{txt}</span>'
  for qval, grp in carto.groupby('quantile'):
    col = grp.color.to_list()[0]
    flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'{qval}'))
    for i, row in grp.iterrows():
      start_coord, end_coord = row.geometry.boundary
      begin = (str(start_coord).split(' ',1)[1])[1:-1]
      begin = begin.split(' ')
      begin = '(' + ' '.join(reversed(begin)) + ')'

      end = (str(end_coord).split(' ',1)[1])[1:-1]
      end = end.split(' ')
      end = '(' + ' '.join(reversed(end)) + ')'

      if row.cnt == 0:
        pol = folium.PolyLine(
        locations=[ [lat,lon] for lon,lat in row.geometry.coords],
        fill_color='#FF0000',
        color='#FF0000',
        popup=folium.Popup(f'<p>Daily Counts: <b>{round(row.cnt)}</b></br>Mean Counts (1h): <b>{round(row.media)}</b></br>Poly cid: <b>{row.poly_cid}</b></br>Poly lid: <b>{row.poly_lid}</b></br>Bound Coords: <b>{begin} - {end}</b></p>', show=False, sticky=True),
      )
      else:
        pol = folium.PolyLine(
          locations=[ [lat,lon] for lon,lat in row.geometry.coords],
          fill_color=col,
          color=col,
          popup=folium.Popup(f'<p>Daily Counts: <b>{round(row.cnt)}</b></br>Mean Counts (1h): <b>{round(row.media)}</b></br>Poly cid: <b>{row.poly_cid}</b></br>Poly lid: <b>{row.poly_lid}</b></br>Bound Coords: <b>{begin} - {end}</b></p>', show=False, sticky=True),
        )
      flayer_sel.add_child(pol)
    m.add_child(flayer_sel)

  coils_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'er_barriers.csv')
  coils = pd.read_csv(coils_file, sep=';')
  dir_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'coils-dir-mapping_template_0.50.csv')
  dirs = pd.read_csv(dir_file, sep=';')
  coils_yep = coils[ coils.Description.isin(dirs.coil_id.values) ]
  flayer_coils = folium.FeatureGroup(name=layerlabel.format(col='blue', txt='selected coil'))
  for cid, row in coils_yep.iterrows():
    pt = folium.CircleMarker(
      location=[row.Lat, row.Lon],
      radius=5,
      fill_color='blue',
      color='blue',
      popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
    )
    flayer_coils.add_child(pt)
  m.add_child(flayer_coils)
  coils_nope = coils[ ~coils.Description.isin(dirs.coil_id.values) ]
  flayer_nope = folium.FeatureGroup(name=layerlabel.format(col='red', txt='coil'))
  for cid, row in coils_nope.iterrows():
    pt = folium.CircleMarker(
      location=[row.Lat, row.Lon],
      radius=5,
      fill_color='red',
      color='red',
      popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
    )
    flayer_nope.add_child(pt)
  m.add_child(flayer_nope)

  # sources_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_sources.csv')
  sources_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_ws', 'output', 'sim_100_sources.csv')
  sources = pd.read_csv(sources_file, sep=';')
  flayer_nodesources = folium.FeatureGroup(name=layerlabel.format(col='black', txt='node sources'))
  for _, row in sources.iterrows():
    pt = folium.CircleMarker(
      location=[row.lat_node, row.lon_node],
      radius=3,
      fill_color='black',
      color='black',
      popup=folium.Popup(f'<p>Node Source <br>{row.tag} </p>', show=False, sticky=True),

    )
    flayer_nodesources.add_child(pt)
  m.add_child(flayer_nodesources)

  flayer_sources = folium.FeatureGroup(name=layerlabel.format(col='blue', txt='sources'))
  for _, row in sources.iterrows():
    pt_src = folium.CircleMarker(
      location=[row.lat_src, row.lon_src],
      radius=3,
      fill_color='blue',
      color='blue',
      popup=folium.Popup(f'<p>Source <br>{row.tag}</p>', show=False, sticky=True),
    )
    flayer_sources.add_child(pt_src)
  m.add_child(flayer_sources)

  # folium.map.LayerControl(collapsed=False).add_to(m)
  folium.map.LayerControl(collapsed=True).add_to(m)
  e, s, w, n = carto.total_bounds
  m.fit_bounds([ [s,w], [n,e] ])
  tok = uniq_file.split('_')
  file_name = tok[0]+ '_' + tok[1]
  html_file = f'{file_name}.html'
  m.save(html_file)
  print(f'File saved: {os.path.abspath(html_file)} ')


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cartogeo', help='carto geojson file', required=False)
  parser.add_argument('-u', '--uniq_cnt', help='input minimocas uniq_cnt csv', required=True)
  args = parser.parse_args()

  create_map = fluxes_map(args.uniq_cnt, args.cartogeo)

