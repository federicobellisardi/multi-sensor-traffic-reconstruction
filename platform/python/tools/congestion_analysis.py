#! /usr/bin/env python3

from collections import defaultdict
from shapely.geometry import Point
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import glob
import pytz
import os

import warnings
warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)

def load_carto():
  carto_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra','er-carto.geojson')
  carto_df = gpd.read_file(carto_file)
  return carto_df

def cid2lid(geojson_network):
  cid_to_lid = defaultdict(int) 
  for lid, cid in zip(carto_df['poly_lid'], carto_df['poly_cid']):
    cid_to_lid[cid] = lid
  return cid_to_lid

def cluster_road_speed(pro_file):
  pro =  pd.read_csv(network_pro_file, sep=r"\s+", engine='python')
  pro['poly_lid'] = pro['#poly_cid'].map(cid2lid)
  X = pro[['speed']]
  num_clusters = 4
  kmeans = KMeans(n_clusters=num_clusters, random_state=42)
  pro['cluster'] = kmeans.fit_predict(X)
  cluster_means = pro.groupby('cluster')['speed'].mean()
  sorted_clusters = cluster_means.sort_values(ascending=True)
  cluster_mapping = {cluster: i for i, cluster in enumerate(sorted_clusters.index)}
  pro['cluster'] = pro['cluster'].map(cluster_mapping)
  lid_to_cluster = defaultdict(int) 
  for lid, cluster in zip(pro['poly_lid'], pro['cluster']):
    lid_to_cluster[lid] = cluster
  return lid_to_cluster

def haversine_distance(point1, point2):
  import math
  lat1,lon1 = point1.x , point1.y
  lat2,lon2 = point2.y , point2.x
  phi1 = math.radians(lat1)
  phi2 = math.radians(lat2)
  lambda1 = math.radians(lon1)
  lambda2 = math.radians(lon2)
  delta_phi = phi2-phi1
  delta_lambda = lambda2-lambda1
  a = math.sin(delta_phi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2.0)**2
  c = 2*math.atan2(math.sqrt(a),math.sqrt(1-a))
  R = 6371  # radius of Earth in kilometers
  d = R*c # d is the distance
  return d

def color_map(val):
  color_dict = {
    0: '#FF0000',   # Red
    1: '#FFFF00',   # Yellow
    2: '#0000FF',   # Blue
    3: '#000000'    # Black
  }
  return color_dict.get(val, '')

def geoloc_poly(carto_df, plid, dict_cluster):
  import folium
  map_center = carto_df.to_crs(epsg=3003).centroid.to_crs(epsg=4326)
  map_center = [ map_center.y.mean(), map_center.x.mean() ]
  m = folium.Map(location=map_center, control_scale=True)

  layerlabel = '<span style="color: {col};">{txt}</span>'

  if len(plid) != 0:
    carto_df = carto_df.loc[carto_df['poly_lid'].isin(plid)]  
  else:
    print(f'Compute road with radius {r}')
    center = [44.494887, 11.3426163]              # Bologna Center
    # center =[44.59445, 11.04979]                #Calstelfranco Emilia Center
    carto_df['distance'] = carto_df['geometry'].apply(lambda geom: haversine_distance(Point(center), geom.centroid))
    carto_df = carto_df[carto_df['distance'] < r]
    carto_df = carto_df.loc[~carto_df['poly_lid'].isin(inside_poly)]

  carto_df['cluster'] = carto_df['poly_lid'].map(dict_cluster)
  carto_df['color'] = carto_df['cluster'].apply(color_map)

  for clus, grp in carto_df.groupby('cluster'):
    col = grp.color.to_list()[0]
    flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'Cluster {int(clus)}'))
    for i, row in grp.iterrows():
      pol = folium.PolyLine(
        locations=[ [lat,lon] for lon,lat in row.geometry.coords],
        fill_color=col,
        color=col,
        popup=folium.Popup(f'<p>Poly Lid: <b>{row.poly_lid}', show=False, sticky=True),
      )
      flayer_sel.add_child(pol)
    m.add_child(flayer_sel)
  folium.map.LayerControl(collapsed=True).add_to(m)
  e, s, w, n = carto_df.total_bounds
  m.fit_bounds([ [s,w], [n,e] ])
  file_name = f'geoloc_poly'
  html_file = f'{save_folder}/{file_name}.html'
  m.save(html_file)
  print(f'Cartography File saved in {os.path.abspath(html_file)} ')
  return carto_df

def get_poly_length(plids):
  carto_df = load_carto()
  lid_to_length = pd.Series(carto_df['poly_length'].values, index=carto_df['poly_lid']).to_dict()
  lid_to_length = {plid: lid_to_length[plid] for plid in plids}
  return lid_to_length

def make_plot(df, save_folder, datetime, boundaries):
  w, h, d = 12, 7, 100
  fig, (ax1, ax2)=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
  ax1.scatter(df['mean_density'], df['mean_speed'], c='DarkBlue', s=40)
  ax1.set_xlim(boundaries[0][0])
  ax1.set_ylim(boundaries[0][1])
  ax1.set_title(f'Speed')
  ax1.set_xlabel(f"Density")
  ax1.set_ylabel(f"Speed")
  ax1.grid()

  ax2.scatter(df['mean_density'], df['mean_flow'], c='Red', s=40)
  ax2.set_xlim(boundaries[1][0])
  ax2.set_ylim(boundaries[1][1])
  ax2.set_title(f'Flow')
  ax2.set_xlabel(f"Density")
  ax2.set_ylabel(f"Flow")
  ax2.grid()

  plt.suptitle(f'Fundamental Diagram - R={r}')
  plt.tight_layout()
  fig.subplots_adjust(top=0.90)
  plt_title = f"{save_folder}/{datetime}_{freq}_fund_diagram.png"
  plt.savefig(plt_title, dpi=150)
  # print(f'File saved: {os.path.abspath(plt_title)} ')

def get_df(data_folder, save_folder):
  target = 'pawn'
  matching_files = [file for file in glob.glob(os.path.join(data_folder, f"*{target}*")) if os.path.isfile(file)]
  df = pd.DataFrame(columns = {'poly_lid', 'speed','flow', 'uniq_counter', 'poly_length', 'density','aug'})
  for file_name in matching_files:
    augmentation = int(file_name.split('/')[-1].split('_')[1])
    file = pd.read_csv(file_name, sep = ';', header=[0])
    file['datatime'] = pd.to_datetime(file['timestamp'], unit='s')
    file = file.loc[(file.poly_lid.isin(plids)) & (file.speed > 0) & (file.s != 0) & (file.flow > 0)]
    # file = file.loc[file['tag'] != "rnd_rnd"]
    file['speed'] = file['speed'] * 3.6
    file = file.groupby([pd.Grouper(key='datatime', freq=freq), 'poly_lid']).agg({'speed': 'mean', 'flow': 'mean', 'pawn_id' : lambda x: x.nunique()})
    file = file.reset_index(level=1).rename(columns={'pawn_id':'uniq_counter'})
    file['poly_length'] = file['poly_lid'].map(poly_length) / 1000
    file['density'] = file['uniq_counter'] / file['poly_length']
    file['aug'] = augmentation
    df = pd.concat([df, file])

  df = df.reset_index()
  df['cluster'] = df['poly_lid'].map(cluster_dict)

  mean_df = pd.DataFrame(columns = ['index', 'aug', 'mean_density','mean_speed', 'mean_flow', 'cluster_num'])
  for clus_n, df_cluster in df.groupby('cluster'):
    for (qhour, aug), df_qh in df_cluster.groupby(['index', 'aug']):
      df_qh['mean_density'] = df_qh['density'].mean()
      df_qh['mean_flow'] = df_qh['flow'].mean()
      df_qh['mean_speed'] = df_qh['speed'].mean()
      df_qh['cluster_num'] = clus_n
      mean_df = pd.concat([mean_df, df_qh[['index', 'aug', 'mean_density', 'mean_speed', 'mean_flow','cluster_num']].iloc[:1]])

  for i, cdf in mean_df.groupby('cluster_num'):
    plot_speed_y_boundary = (cdf['mean_speed'].min(), cdf['mean_speed'].max())
    plot_flow_y_boundary = (cdf['mean_flow'].min(), cdf['mean_flow'].max())
    plot_x_boundary = (cdf['mean_density'].min(), cdf['mean_density'].max())
    boundary_1 = (plot_x_boundary, plot_speed_y_boundary)
    boundary_2 = (plot_x_boundary, plot_flow_y_boundary)
    for qhour, df_plot in cdf.groupby('index'):
      day = qhour.strftime(short_fmt)[:6]
      save_plot = save_folder + f'/radius_{r}/{day}/cluster_{i}/freq_{freq}'
      if not os.path.exists(save_plot): os.makedirs(save_plot, exist_ok=True)
      plot = make_plot(df_plot, save_plot, qhour.strftime(short_fmt), (boundary_1, boundary_2))
  return df


if __name__ == '__main__':
  pd.options.mode.chained_assignment = None
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--data_folder', help='pawn input folder')
  parser.add_argument('-o', '--output_folder', help='output folder')
  parser.add_argument('-l','--poly_list', nargs='+', help='list of polylines')
  parser.add_argument('-f','--freq', type=int, help='sampling dt', default = 900)
  parser.add_argument('-r', '--radius', type=int, default=7, help='Radius of the analysis - default 7')
  args = parser.parse_args()

  plids = [] if args.poly_list == None else args.poly_list
  inside_poly = [3895, 3896, 3897, 3898, 4122, 3899, 3801, 3900, 3901, 3902, 3903, 3907] # Links inside the tangenziale of Bologna
  r = args.radius
  freq = f'{args.freq}s'
  short_fmt = '%y%m%d_%H%M%S'
  tz_rome = pytz.timezone('Europe/Rome')
  
  if not os.path.exists(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_congestion')):
    os.makedirs(os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_congestion'), exist_ok=True)
  network_pro_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'carto', 'er-speed.pro')

  pawn_folder = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_congestion', 'pawn_folder') if args.data_folder == None else args.data_folder
  if not os.path.exists(pawn_folder): print(f"Check the pawn folder")
  save_folder = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_congestion', f'output') if args.output_folder == None else os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_congestion', f'{args.output_folder}')
  if not os.path.exists(save_folder): os.makedirs(save_folder, exist_ok=True)

  carto_df = load_carto()
  cid2lid = cid2lid(carto_df)
  cluster_dict = cluster_road_speed(network_pro_file)
  carto_df = geoloc_poly(carto_df, plids, cluster_dict)
  plids = carto_df['poly_lid'].tolist()

  poly_length = get_poly_length(plids)
  df = get_df(pawn_folder, save_folder)