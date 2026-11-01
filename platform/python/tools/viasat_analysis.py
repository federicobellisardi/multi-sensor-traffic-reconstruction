#! /usr/bin/env python3
# python ../python/tools/viasat_analysis.py -c conf.json -l forli


import os
import glob
import json
import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import folium
from matplotlib import cm
from matplotlib.colors import to_hex, rgb2hex
import scipy.spatial.distance as ssd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class viasat:

  def __init__(self):
    self.ncluster = 3
    self.polylist = []
    self.viasatfile = viasatfile
    self.viasat_df = pd.DataFrame()
    self.uniq_df = pd.DataFrame()
    self.penetrazione_df = pd.DataFrame()
    self.cluster_df = pd.DataFrame()
    self.log_cluster_df = pd.DataFrame()
    self.cluster_dict = dict()

  def dist(self, a, b, t='euclidean'):
    if t == 'euclidean':
      return np.sqrt(np.sum((a-b)**2)) # or   ssd.euclidean(a,b)
    elif t == 'correlation':
      return ssd.correlation(a,b)

  def norm(self, a):
    tot = a.sum()
    if tot!=0: return a/tot
    else:      return a

  def poly_filter(self, polycid):
    poly_mask = []
    if len(polycid)!=0:
      for i in polycid:
        poly_id = int(i)
        poly_mask.append(poly_id)
    else:
      all_poly = v.viasat_builder(self.viasatfile)
      poly_mask = list(all_poly.columns)
    return poly_mask    

  def major_cluster(self, df, carto, outname):
    if outname == 'Log_':
      df['penetration'] = (round(df.log_penetration, 0)).astype(int)

    scaled_df = StandardScaler().fit_transform(df)
    kmeans_kwargs = {
      "init": "random",
      "n_init": 10,
      "random_state": 1,
    }

    sse = []
    for k in range(1, 11):
        kmeans = KMeans(n_clusters=k, **kmeans_kwargs)
        kmeans.fit(scaled_df)
        sse.append(kmeans.inertia_)

    plt.plot(range(1, 11), sse)
    plt.xticks(range(1, 11))
    plt.xlabel("Number of Major Clusters")
    plt.ylabel("SSE")
    plt.clf()
    plt.close()
    # plt.show()
    kmeans = KMeans(init="random", n_clusters=self.ncluster, n_init=10, random_state=1)
    kmeans.fit(scaled_df)
    df['cluster'] = kmeans.labels_

    merged = df.join(carto.geometry)
    merged['cid'] = merged.index

    n_cluster = sorted(list(merged.cluster.unique()))
    c_map = cm.get_cmap('gnuplot', len(n_cluster))
    rgb_scale = c_map(n_cluster)
    color_scale = [rgb2hex(r) for r in rgb_scale]
    cluster_col = dict(zip(n_cluster, color_scale))
    merged['color'] = merged.cluster.map(cluster_col)

    if outname == 'Log_':
      self.log_cluster_df = merged.copy()
    else:
      self.cluster_df = merged.copy()

    m = folium.Map(location=center_coords, control_scale=True)
    import warnings
    warnings.filterwarnings("ignore")
    layerlabel = '<span style="color: {col};">{txt}</span>'
    for clus, grp in merged.groupby('cluster'):
      col = grp.color.to_list()[0]
      flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'Cluster n°{clus+1}'))
      for i, row in grp.iterrows():
        start_coord, end_coord = row.geometry.boundary
        begin = (str(start_coord).split(' ',1)[1])[1:-1]
        begin = begin.split(' ')
        begin = '(' + ' '.join(reversed(begin)) + ')'

        end = (str(end_coord).split(' ',1)[1])[1:-1]
        end = end.split(' ')
        end = '(' + ' '.join(reversed(end)) + ')'
        if outname == 'Log_':
          pol = folium.PolyLine(
              locations=[ [lat,lon] for lon,lat in row.geometry.coords],
              fill_color=col,
              color=col,
              popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Log Scale - Stat Penetration: <b>{round(row.penetration, 2)}</b></p>', show=False, sticky=True),
          )
        else:
            pol = folium.PolyLine(
              locations=[ [lat,lon] for lon,lat in row.geometry.coords],
              fill_color=col,
              color=col,
              popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Percentage - Stat Penetration: <b>{round(row.penetration, 2)} %</b></p>', show=False, sticky=True),
          )
        flayer_sel.add_child(pol)
      m.add_child(flayer_sel)
    folium.map.LayerControl(collapsed=True).add_to(m)

    if outname == 'Log_':
      html_file = f'{save_penetrazione}/log_Cluster_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
    else:
      html_file = f'{save_penetrazione}/cluster_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
    m.save(html_file)
    print(f'File saved in {os.path.abspath(html_file)}')

  def viasat_builder(self, viasatfile):
    viasat_df = pd.read_csv(viasatfile, sep=';')
    viasat_df.set_index(pd.to_datetime(viasat_df.time), inplace=True)
    self.startdate_sim = viasat_df.index[0]
    self.stopdate_sim = viasat_df.index[-1]
    viasat_df = viasat_df[(viasat_df.index >= self.startdate_sim ) & (viasat_df.index < self.stopdate_sim)]
    viasat_df = viasat_df[['total_fluxes','cid']]
    viasat_df['time_hour'] = viasat_df.index.time
    viasat_df = viasat_df.groupby(['time_hour','cid']).sum()
    viasat_df = viasat_df.unstack(level='cid')
    viasat_df.columns = viasat_df.columns.droplevel(level=0)
    self.viasat_df = viasat_df.loc[:, (viasat_df != 0).any(axis=0)]
    # self.viasat_df = viasat_df[v.poly_filter(polyfilter)]
    return self.viasat_df

  def uniq_builder(self, polyfilter, year):
    self.poly_list = v.poly_filter(polyfilter)
    try:
      if year == '2020':
        uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2020', 'uniq')
      elif year == '2021':
        uniq_path = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'sim2021', 'uniq')
 
      uniq_all = sorted(glob.glob(uniq_path + '/*.csv.corrected'))
      uniq_all_df = pd.DataFrame()
      for uniq_file in uniq_all:
        uniq_df = pd.read_csv(uniq_file, sep=';')
        uniq_df = uniq_df.groupby('poly_cid').sum()
        uniq_df = uniq_df.drop('poly_lid', axis=1)
        uniq_df.columns = pd.to_datetime(uniq_df.columns)
        uniq_df = uniq_df.loc[self.poly_list]
        uniq_df = uniq_df.T
        uniq_df.index.rename('datetime', inplace=True)
        # uniq_df.index = uniq_df.index.tz_localize(None).tz_convert('Europe/Rome')
        uniq_df['new_time'] = [i+timedelta(minutes=75) for i in uniq_df.index]
        uniq_df.set_index('new_time', inplace=True)
        uniq_df['hour'] = [int(str(i).split(' ')[-1].split(':')[0]) for i in uniq_df.index]
        datetime_list = [i for i in uniq_df.index.to_list() if "15:00" in str(i)]
        uniq_df = uniq_df.groupby(by='hour').sum()
        uniq_df['datetime'] = datetime_list
        uniq_df.set_index('datetime', inplace=True)
        uniq_df['time_index'] = uniq_df.index.time
        uniq_df.set_index('time_index', inplace=True)
        uniq_all_df=pd.concat([uniq_all_df, uniq_df], axis=1).fillna(0)
      self.uniq_df = uniq_all_df.groupby(by=uniq_all_df.columns, axis=1).mean()
    except Exception as e:
      print("Error: ", e)
    return self.uniq_df

  def penetrazione(self, carto):
    print(f"-> Start Statistical Penetration\n")
    penetration_list = []
    log_penetration_list = []
    for col in self.uniq_df.columns:
      uniq_single = self.uniq_df[col]
      viasat_single = self.viasat_df[col]

      unique_sum = uniq_single.to_numpy().sum()
      viasat_sum = viasat_single.to_numpy().sum()
      if unique_sum == 0: continue
      penetration = viasat_sum / unique_sum
      log_penetration = np.log10(penetration)
      penetration = penetration * 100
      penetration_list.append((col,penetration))
      log_penetration_list.append((col, log_penetration))

    penetration_df = pd.DataFrame(penetration_list, columns=['poly_cid','penetration'])
    penetration_df.set_index('poly_cid', inplace=True)
    self.penetrazione_df = penetration_df.copy()
    log_penetration_df = pd.DataFrame(log_penetration_list, columns=['poly_cid','log_penetration'])
    log_penetration_df.set_index('poly_cid', inplace=True)
    
    print(f"-> -> Creating .html Major Cluster")
    cluster_plot = v.major_cluster(penetration_df, carto, '')
    cluster_log_plot = v.major_cluster(log_penetration_df, carto, 'Log_')
    print(f"-> -> Done - .html Major Cluster\n")

    ## Plot Stat Penetration %
    max_hight = penetration_df.values.max() + 0.25*penetration_df.values.max()
    w, h, d = 12, 7, 100
    fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
    tsd = [ p for p in range(len(penetration_df.index)) ]
    tusd = 1
    lusd = 1
    tsd_ticks = tsd[::tusd]
    tsd_lbl = [ str(p) for p in penetration_df.index ]
    tsd_lbl = tsd_lbl[::lusd]
    width = 0.8
    bar_1 = ax.bar(tsd, penetration_df.penetration, width=width)
    for rect in bar_1:
      height = rect.get_height()
      ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
    ax.set_xticks(tsd_ticks)
    ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
    ax.set_ylabel('Penetration [%]')
    ax.set_xlabel('Poly CID')
    ax.set_ylim(0, max_hight)
    plt.title(f'Statistic penetration from {str(self.startdate_sim).split(" ")[0]} to {str(self.stopdate_sim).split(" ")[0]}\n viasat/sim')

    outname = os.path.join(save_penetrazione, f'penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
    fig.savefig(outname, dpi=150)
    print(f'  Image saved in {outname}')
    plt.clf()
    plt.close()

    # Sorted df
    penetration_df_sorted = penetration_df.sort_values(by=['penetration'], ascending=False)
    w, h, d = 12, 7, 100
    fig,ax=plt.subplots(1, 1, figsize=(w, h), dpi=d)
    tsd = [ p for p in range(len(penetration_df_sorted.index)) ]

    tusd = 1
    lusd = 1
    tsd_ticks = tsd[::tusd]
    tsd_lbl = [ str(p) for p in penetration_df_sorted.index ]
    tsd_lbl = tsd_lbl[::lusd]
    width = 0.8
    bar_1 = ax.bar(tsd, penetration_df_sorted.penetration, width=width, label=f'Mean Value = {penetration_df_sorted.penetration.mean():.1f} %')
    # for rect in bar_1:
    #   height = rect.get_height()
    #   ax.text(rect.get_x() + rect.get_width() / 2.0, height, f'{height:.1f}%', ha='center', va='bottom')
    ax.set_xticks(tsd_ticks)
    ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
    ax.set_ylabel('Penetration [%]')
    ax.set_xlabel('Poly CID')
    ax.set_ylim(0, max_hight)
    ax.legend(loc='upper left')
    plt.title(f'Sorted statistic penetration from {str(self.startdate_sim).split(" ")[0]} to {str(self.stopdate_sim).split(" ")[0]}\n viasat/sim')
    outname = os.path.join(save_penetrazione, f'sorted_penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
    fig.savefig(outname, dpi=150)
    print(f'  Image saved in {outname}')
    plt.clf()
    plt.close()

    # Log Scale
    log_penetration_df['round_value'] = (round(log_penetration_df.log_penetration, 0)).astype(int)
    fig, axh = plt.subplots(1, 1,figsize=(w,h), dpi=d)
    log_penetration_df['round_value'].value_counts().plot(kind='bar', rot=0, width=.5)

    axh.set_xlabel(f'Log scale')
    axh.set_ylabel("Occurencies")
    axh.yaxis.grid(True, linestyle='-')
    plt.title(f"Log Scale penetration distribution")
    outname2 = os.path.join(save_penetrazione, f'histlog_penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.png')
    fig.savefig(outname2, dpi=150)
    print(f'  Image saved in {outname2}')
    plt.clf()
    plt.close()
    print(f"-> Done - Statistical Penetration")

  def geo_pen(self, carto):
    print(f'->  Creating quantile penetration and Coils geoloc html file')
    merged = self.penetrazione_df.join(carto.geometry)
    merged['cid'] = merged.index
    quantiles_val = [0.0, 0.20, 0.40, 0.60, 0.80, 0.90, 1.0]
    quantiles = self.penetrazione_df.penetration.quantile(quantiles_val).to_list()
    bins = [float(q) for q in quantiles]
    cmap = cm.get_cmap('seismic', len(bins)-1)
    rgb_scale = cmap(quantiles_val)
    color_scale = [rgb2hex(r) for r in rgb_scale]
    color_scale = color_scale[:-1]
    default_color = color_scale[1]
    map_col_quantil={}
    for i in np.arange(0, len(color_scale)):
      label = f'{quantiles_val[i]} < q <= {quantiles_val[i+1]}'
      map_col_quantil[color_scale[i]]=label

    list_color = pd.cut(merged.penetration, bins=bins, labels=color_scale)
    merged['color'] = list_color.to_list()
    merged.color.fillna(default_color, inplace=True)
    merged['quantile'] = [map_col_quantil[i] for i in merged.color]

    merged.sort_values(by='quantile', inplace=True)

    m = folium.Map(location=center_coords, control_scale=True)
    import warnings
    warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)

    layerlabel = '<span style="color: {col};">{txt}</span>'
    for qval, grp in merged.groupby('quantile'):
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

        pol = folium.PolyLine(
            locations=[ [lat,lon] for lon,lat in row.geometry.coords],
            fill_color=col,
            color=col,
            popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></br>Penetrazione Statistica: <b>{round(row.penetration, 2)} %</b></p>', show=False, sticky=True),
        )
        flayer_sel.add_child(pol)
      m.add_child(flayer_sel)
    coils_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'er_barriers.csv')
    coils = pd.read_csv(coils_file, sep=';')
    dir_file = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'coils-dir-mapping_template_0.50.csv')
    dirs = pd.read_csv(dir_file, sep=';')
    coils_yep = coils[ coils.Description.isin(dirs.coil_id.values) ]
    coils_yep = coils_yep.loc[coils_yep.PRO =='FO']
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
    coils_nope = coils_nope.loc[coils_nope.PRO =='FO']

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
    folium.map.LayerControl(collapsed=True).add_to(m)
    html_file = f'{save_penetrazione}/penetrazione_statistica_{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}.html'
    m.save(html_file)
    print(f'File saved: {os.path.abspath(html_file)} ')
    print(f"->  Done quantile penetration html file")

  def norm_analysis(self, test_mode):
    print(f"->  Start local analysis")
    uniq_df = self.uniq_df.loc[:, (self.uniq_df != 0).any(axis=0)]
    viasat_df = self.viasat_df.copy()

    if len(uniq_df.columns) > 40: uniq_df = uniq_df.sample(10, axis=1)
    if args.test_mode == True: 
      print('Test mode Enabled')
      poly_col = [23357, 23511, 23909, 31724, 31785, 32114, 32250, 32704, 32724, 32739, 33149, 33322, 33619, 33818, 33828, 34018]
      uniq_df = uniq_df[poly_col]
  
    for col in uniq_df.columns:
      uniq_norm = uniq_df[col]/uniq_df[col].sum()
      viasat_norm = viasat_df[col]/viasat_df[col].sum()

      diff_df = viasat_norm.copy().to_frame().rename(columns={col:"viasat_cnt"})
      diff_df['uniq_cnt'] = uniq_norm.values
      diff_df['perc_diff'] = (diff_df.uniq_cnt - diff_df.viasat_cnt) * 100
      y_limits = max(abs(diff_df.perc_diff)) + 2/100 * max(abs(diff_df.perc_diff))

      w, h, d = 12, 7, 150
      fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
      tsd = [ t for t in range(len(viasat_norm.index)) ]
      tusd = 1
      lusd = 1
      tsd_ticks = tsd[::tusd]
      tsd_lbl = [ t.strftime('%H:%M') for t in viasat_norm.index ]
      tsd_lbl = tsd_lbl[::lusd]
      ax = axs[0]
      ax.plot(tsd, uniq_norm, color='C0', label='Normalized sim mean data')
      ax.set_ylabel('Norm SIM', color="C0")
      ax.grid()
      ax.legend(loc='upper left')
      ax2=ax.twinx()
      ax2.plot(tsd, viasat_norm, '--', color="C1", label='Normalized VIASAT sum data')
      ax2.set_ylabel('Norm viasat', color="C1")
      ax2.legend(loc='upper right')

      ax1 = axs[1]
      ax1.plot(tsd, diff_df.perc_diff, color='k', label='Difference simulation - viasat data')
      ax1.set_ylabel('Percentage difference [%]', color="k")
      ax1.set_xlabel('Time (H:M:S)')
      ax1.set_xticks(tsd_ticks)
      ax1.set_xticklabels(tsd_lbl, rotation=45)
      ax1.set_ylim(-y_limits, y_limits)
      ax1.grid()
      ax1.legend(loc='upper left')

      string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
      string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
      plt.title(f'Poly cid {col} \n{string_title_text}')
      plt.tight_layout()

      single_save = f'{save_folder}/local_anomalies'
      if not os.path.exists(single_save): os.makedirs(single_save)

      outname = os.path.join(single_save, f'cid_{col}_{string_save_text}.png')
      fig.savefig(outname, dpi=150)
      print(f'Image saved in {outname}')
      plt.clf()
      plt.close()
    print(f"->  Done local analysis")

  def cluster_analysis(self, outtype):
    print("-> Start Cluster Analysis")
    from scipy.stats import norm
    cluster_dict = dict()
    if outtype == 'Log_':
      for cluster_num, single_cluster in self.log_cluster_df.groupby('cluster'):
        cluster_dict[cluster_num] = single_cluster.index.values.tolist()
    else:
      for cluster_num, single_cluster in self.cluster_df.groupby('cluster'):
        cluster_dict[cluster_num] = single_cluster.index.values.tolist()

    self.cluster_dict = cluster_dict
    inverse = { v: k for k, l in cluster_dict.items() for v in l }

    daily_sum = self.uniq_df.sum().reset_index()
    daily_sum = daily_sum.rename(columns={0: "sim_cnt"})
    viasat_daily_sum = self.viasat_df.sum().reset_index()
    viasat_daily_sum = viasat_daily_sum.rename(columns={0: "viasat_counter"})
    viasat_daily_cnt = pd.Series(viasat_daily_sum.viasat_counter.values,index=viasat_daily_sum.cid).to_dict()

    daily_sum['viasat_cnt'] = daily_sum['poly_cid'].map(viasat_daily_cnt)
    daily_sum['cluster'] = daily_sum['poly_cid'].map(inverse)
    daily_sum["ratio"] = daily_sum['viasat_cnt'] / daily_sum['sim_cnt']
    daily_sum.set_index('poly_cid', inplace=True)

    dendrogram = v.dendrogram(self.uniq_df, cluster_dict)

    for key, values in cluster_dict.items():
      uniq_df = self.uniq_df[values]
      uniq_df = uniq_df.loc[:, (self.uniq_df != 0).any(axis=0)]
      viasat_df = self.viasat_df.copy()

      uniq_scaled_list = []
      viasat_scaled_list = []

      if outtype == 'Log_':
        for col in uniq_df.columns:
          uniq_norm = uniq_df[col]/uniq_df[col].sum()
          viasat_norm = viasat_df[col]/viasat_df[col].sum()
          uniq_scaled_list.append(uniq_norm)
          viasat_scaled_list.append(viasat_norm)
        uniq_scaled_df = pd.DataFrame(uniq_scaled_list).T
        viasat_scaled_df = pd.DataFrame(viasat_scaled_list).T

        viasat_scaled_df = viasat_scaled_df[uniq_scaled_df.columns]
        df_1_stat = pd.DataFrame(index=uniq_scaled_df.index, columns=['media', 'std_dev'])  
        df_1_stat['media'] = uniq_scaled_df.mean(axis=1)
        df_1_stat['std_dev'] = uniq_scaled_df.std(axis=1)

        df_2_stat = pd.DataFrame(index=viasat_scaled_df.index, columns=['media', 'std_dev'])  
        df_2_stat['media'] = viasat_scaled_df.mean(axis=1)
        df_2_stat['std_dev'] = viasat_scaled_df.std(axis=1)
        
        uniq_stat = pd.concat([uniq_scaled_df,df_1_stat], axis=1).reset_index()
        uniq_stat = uniq_stat.drop(columns='time_index')
        uniq_stat.set_index(df_2_stat.index, inplace=True)

        viasat_stat = pd.concat([viasat_scaled_df,df_2_stat], axis=1).reset_index()
        viasat_stat = viasat_stat.drop(columns='time_hour')
        viasat_stat.set_index(df_2_stat.index, inplace=True)

        def euc_dist(first, second):
          euc_dict = dict()
          for col in first.columns:
            first_df = first[col]
            second_df = second[col]
            euc_dict[col] = np.sqrt(np.sum((first_df - second_df) ** 2))
          return euc_dict

        euclidean_dict = euc_dist(uniq_stat,viasat_stat)
        names = list(euclidean_dict.keys())
        values = list(euclidean_dict.values())

        plt.bar(range(len(names)), values, width = .5, color='b')
        string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
        plt.title(f'Cluster {key} - Distribution of euclidean distances\n{string_title_text}')
        plt.xlabel("Polylines")

        string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
        cluster_la = f'{save_folder}/local_anomalies'
        if not os.path.exists(cluster_la): os.makedirs(cluster_la)
        cluster_dist = f'{cluster_la}/log_cluster_distances'
        if not os.path.exists(cluster_dist): os.makedirs(cluster_dist)
        outname_dist = os.path.join(cluster_dist, f'log_cluster_{key}_distance_{string_save_text}.png')
        plt.savefig(outname_dist, dpi=150)
        print(f'  Image saved in {outname_dist}')
        plt.close()
        plt.clf()

        w, h, d = 12, 7, 150
        fig, axa=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
        tsd = [ t for t in range(len(df_1_stat.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ t.strftime('%H:%M') for t in df_2_stat.index ]
        tsd_lbl = tsd_lbl[::lusd]
        ax = axa[0]
        ax.plot(tsd, df_1_stat.media, color='k', label=f'Sim Mean in cluster #{key}')
        ax.fill_between(tsd, df_1_stat.media - df_1_stat.std_dev, df_1_stat.media + df_1_stat.std_dev, alpha = 0.4, label=f'Std Sim #{key}')
        
        ax.plot(tsd, df_2_stat.media, '-',color='b', label=f'Viasat Mean in cluster #{key}')
        ax.fill_between(tsd, df_2_stat.media - df_2_stat.std_dev, df_2_stat.media + df_2_stat.std_dev, color='yellow', alpha = 0.2, label=f'Std Viasat #{key}')
        ax.set_ylabel('Norm counter', color="k")
        ax.grid()
        ax.legend(loc='upper left')

        df_reset = df_1_stat[['media']].reset_index()
        df_reset['time_hour'] = df_2_stat.index
        df_reset = df_reset.drop(columns="time_index")
        df_reset.set_index(df_reset.time_hour, inplace=True)
        df_l2 = pd.concat([df_reset['media'], df_2_stat['media']], axis=1, keys=['media_uniq', 'media_viasat'])
        df_l2['euc_dist'] = np.sqrt((df_l2.media_uniq - df_l2.media_viasat) ** 2)

        ax = axa[1]
        ax.bar(tsd, df_l2.euc_dist, color='blue', label=f'Euclidean distance in cluster #{key}')
        ax.set_ylabel('Euclidean distance', color="k")
        # ax.grid()
        ax.legend(loc='upper left')
        ax.set_xticks(tsd_ticks)
        ax.set_xticklabels(tsd_lbl, rotation=45, ha='right')
        ax.set_ylim(0,.04)
        ax.set_xlabel('Datetime')

        plt.suptitle(f"Cluster # {key}\n{string_title_text}")
        cluster_mean_save = f'{cluster_la}/log_cluster_mean'
        if not os.path.exists(cluster_mean_save): os.makedirs(cluster_mean_save)
        outname = os.path.join(cluster_mean_save, f'log_cluster_mean_{key}_{string_save_text}.png')
        plt.savefig(outname, dpi=150)
        # plt.show()
        plt.clf()
        plt.close()
        print(f'  Image saved in {outname}')


      if len(uniq_df.columns) > 40: uniq_df = uniq_df.sample(10, axis=1)

      for col in uniq_df.columns:
        uniq_norm = uniq_df[col]/uniq_df[col].sum()
        viasat_norm = viasat_df[col]/viasat_df[col].sum()

        diff_df = viasat_norm.copy().to_frame().rename(columns={col:"viasat_cnt"})
        diff_df['uniq_cnt'] = uniq_norm.values
        diff_df['perc_diff'] = (diff_df.uniq_cnt - diff_df.viasat_cnt) * 100
        y_limits = max(abs(diff_df.perc_diff)) + 2/100 * max(abs(diff_df.perc_diff))

        w, h, d = 12, 7, 150
        fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
        tsd = [ t for t in range(len(viasat_norm.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ t.strftime('%H:%M') for t in viasat_norm.index ]
        tsd_lbl = tsd_lbl[::lusd]
        ax = axs[0]
        ax.plot(tsd, uniq_norm, color='C0', label='Normalized sim mean data')
        ax.set_ylabel('Norm SIM', color="C0")
        ax.grid()
        ax.legend(loc='upper left')
        ax2=ax.twinx()
        ax2.plot(tsd, viasat_norm, '--', color="C1", label='Normalized VIASAT sum data')
        ax2.set_ylabel('Norm viasat', color="C1")
        ax2.legend(loc='upper right')

        ax1 = axs[1]
        ax1.plot(tsd, diff_df.perc_diff, color='k', label='Difference simulation - viasat data')
        ax1.set_ylabel('Percentage difference [%]', color="k")
        ax1.set_xlabel('Time (H:M:S)')
        ax1.set_xticks(tsd_ticks)
        ax1.set_xticklabels(tsd_lbl, rotation=45)
        ax1.set_ylim(-y_limits, y_limits)
        ax1.grid()
        ax1.legend(loc='upper left')

        string_save_text = str(self.startdate_sim).split(' ')[0].replace('-','') +  str(self.stopdate_sim).split(' ')[0].replace('-','')
        string_title_text = 'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
        if outtype == 'Log_':
          plt.title(f'Log Cluster {key}\nPoly cid {col} \n{string_title_text}')
        else:
          plt.title(f'Cluster {key}\nPoly cid {col} \n{string_title_text}')
        plt.tight_layout()

        single_save = f'{save_folder}/cluster_analysis'
        if not os.path.exists(single_save): os.makedirs(single_save)
        if outtype == 'Log_':
          cluster_save = f'{single_save}/log_cluster_{key}'
          if not os.path.exists(cluster_save): os.makedirs(cluster_save)
          outname = os.path.join(cluster_save, f'log_cluster_{key}_cid_{col}_{string_save_text}.png')
        else:
          cluster_save = f'{single_save}/cluster_{key}'
          if not os.path.exists(cluster_save): os.makedirs(cluster_save)
          outname = os.path.join(cluster_save, f'cluster_{key}_cid_{col}_{string_save_text}.png')

        fig.savefig(outname, dpi=150)

        print(f'  Image saved in {outname}')
        plt.clf()
        plt.close()    
      print("-> Done - Cluster Analysis")

  def dendrogram(self, df, dict_cluster):
    import scipy.cluster.hierarchy as sch

    clus_major = 2
    dist_type = 'euclidean'
    hca_method = 'ward'
    normalize = False 
    check_2_p = False

    print('-> Creating Dendrogram')
    single_save = f'{save_folder}/cluster_analysis'
    if not os.path.exists(single_save): os.makedirs(single_save)
    df = df.reset_index()
    df.set_index('time_index', inplace=True)
    df = df.loc[:, (df != 0).any(axis=0)]
    for key, values in dict_cluster.items():
      if key == clus_major : new_df = df[values]
    tags = list(new_df.columns)
    tagn = len(tags)

    dist_mat = []
    t_mat = []
    for j in range(0,tagn-1):
      for k in range(j+1,tagn):
        if normalize:
          distance = v.dist(v.norm(new_df[tags[j]].values),v.norm(new_df[tags[k]].values),dist_type)
        else:
          distance = v.dist(new_df[tags[j]].values,new_df[tags[k]].values,dist_type)
        t_mat.append([distance,j,k])
    dist_mat.append(t_mat)
    dist_mat = np.array(dist_mat) # pairwise long form distance matrix

    dfdevs = pd.DataFrame()
    dfdevs['tag1']= dist_mat[0,:,1].astype(int)
    dfdevs['tag2']= dist_mat[0,:,2].astype(int)
    dfdevs['poly1'] = [tags[int(a)] for a in dfdevs['tag1'].values]
    dfdevs['poly2'] = [tags[int(a)] for a in dfdevs['tag2'].values]
    dfdevs['std'] = np.std(dist_mat,axis=0)[:,0]
    dfdevs['sum'] = np.sum(dist_mat,axis=0)[:,0]

    # add all columns before sorting
    dfstds = dfdevs.sort_values(by='std')
    dfsums = dfdevs.sort_values(by='sum')

    pos = 0 # Nth best pair
    ordtype = 'sum' # sum or std?


    if   ordtype == 'sum': data = dfsums
    if normalize: titolo+= 'normalized, '
    if check_2_p:
      titolo = f'Poly countings, ordered by curve distance {ordtype}, '
      poly1 = data['poly1'].iloc[pos]
      poly2 = data['poly2'].iloc[pos]
      titolo+= f'{pos+1}° best pair: {poly1} / {poly2}'

      fig, axs=plt.subplots(1, 1, figsize=(12, 7), dpi=150)
      tsd = [ p for p in range(len(new_df.index)) ]
      tusd = 1
      lusd = 1
      tsd_ticks = tsd[::tusd]
      tsd_lbl = [ str(p) for p in new_df.index ]
      if normalize:
        axs.plot(tsd, v.norm(new_df[poly1]), 'r', alpha=0.8)
        axs.plot(tsd, v.norm(new_df[poly2]), 'b', alpha=0.8)
      else:
        axs.plot(tsd, new_df[poly1], 'r', alpha=0.8)
        axs.plot(tsd, new_df[poly2], 'b', alpha=0.8)
      plt.title(titolo)
      plt.xlabel('Date')
      plt.ylabel('Countings')
      plt.legend([poly1,poly2])
      # plt.show()
      plt.clf()
      plt.close()
    else: pass

    ## Plot Dendrogram
    single_save = f'{save_folder}/cluster_analysis'
    if not os.path.exists(single_save): os.makedirs(single_save)
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111)
    linkg = sch.linkage(dfdevs[ordtype].values,method=hca_method)
    sch.dendrogram(linkg, labels=tags)
    plt.title(f'HCA dendrogram method: {hca_method}, distance: {dist_type}\n')
    plt.xticks(fontsize=7)
    plt.savefig(f"{single_save}/inner_dendrogram.png")

    if normalize: cut_distance = 0.4 
    else: cut_distance = 17000 

    clusterlist = sch.fcluster(linkg, cut_distance, criterion='distance')-1
    df_cluster = pd.DataFrame({'cid':tags,'cluster':clusterlist})
    nclusters = len(np.unique(clusterlist))
    df_cluster.set_index(df_cluster.cid, inplace=True)

    merged = df_cluster.join(carto.geometry)
    merged['cid'] = merged.index

    nclusters = sorted(list(merged.cluster.unique()))
    c_map = cm.get_cmap('gnuplot', len(nclusters))
    rgb_scale = c_map(nclusters)
    color_scale = [rgb2hex(r) for r in rgb_scale]
    cluster_col = dict(zip(nclusters, color_scale))
    merged['color'] = merged.cluster.map(cluster_col)

    m = folium.Map(location=center_coords, control_scale=True)
    import warnings
    warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)
    layerlabel = '<span style="color: {col};">{txt}</span>'
    for clus, grp in merged.groupby('cluster'):
      col = grp.color.to_list()[0]
      flayer_sel = folium.FeatureGroup(name=layerlabel.format(col=col, txt=f'Cluster num {clus}'))
      for i, row in grp.iterrows():
        start_coord, end_coord = row.geometry.boundary
        begin = (str(start_coord).split(' ',1)[1])[1:-1]
        begin = begin.split(' ')
        begin = '(' + ' '.join(reversed(begin)) + ')'

        end = (str(end_coord).split(' ',1)[1])[1:-1]
        end = end.split(' ')
        end = '(' + ' '.join(reversed(end)) + ')'
        pol = folium.PolyLine(
            locations=[ [lat,lon] for lon,lat in row.geometry.coords],
            fill_color=col,
            color=col,
            popup=folium.Popup(f'<p>Poly cid: <b>{row.cid}</b></p>', show=False, sticky=True),
        )
        flayer_sel.add_child(pol)
      m.add_child(flayer_sel)
    folium.map.LayerControl(collapsed=True).add_to(m)
    set_date_save = f'{str(self.startdate_sim).split(" ")[0].replace("-","")}_{str(self.stopdate_sim).split(" ")[0].replace("-","")}'
    html_file = f'{single_save}/inner_cluster_{clus_major}_{set_date_save}.html'
    m.save(html_file)
    print(f'   File saved: {os.path.abspath(html_file)} ')

  def smooth(self, df):
    dfsm = pd.DataFrame([], columns=df.columns, index=df.index)
    def box_centered_kernel(tot_len, box_len):
      pad_len = tot_len - box_len
      kern = np.concatenate([
      np.zeros((pad_len // 2)),
      np.ones((box_len)) / box_len,
      np.zeros((pad_len - pad_len // 2))# for odd box_len
      ])
      return kern

    ma_size = 5 # running average idx interval from time in seconds
    kern = box_centered_kernel(len(df), ma_size)
    for c in df.columns:
      conv = np.fft.fftshift(np.real(np.fft.ifft( np.fft.fft( df[c].values ) * np.fft.fft(kern) )))
      dfsm[c] = conv
    return dfsm

  def L2_diff(self):
    print(f"-> -> Start L2 diff sim vs viasat * penetration")
    clus_major = 2
    smooth = False
    norm = True

    df1 = self.uniq_df.copy().loc[:, (self.uniq_df != 0).any(axis=0)]
    for key, values in self.cluster_dict.items():
      if key == clus_major : df = df1[values]
    df2 = self.viasat_df.copy()

    if smooth: 
      df = v.smooth(df)
      df2 = v.smooth(df2)
    else: pass

    for col in df.columns:
      df1_single = df[col]
      df2_single = df2[col]
      pen = df2_single.values.sum() / df1_single.values.sum()
      df2_single = df2_single * (1/pen)
      if norm: l2_diff = np.sqrt((v.norm(df1_single.values)-v.norm(df2_single.values))**2)
      else: l2_diff = np.sqrt((df1_single.values-df2_single.values)**2)

      good = [3419, 3583, 6562, 6580, 9965, 18516, 18561,45594] # Example of good Poly
      if col in good: 
        w, h, d = 10, 8, 100
        fig, axs=plt.subplots(2, 1, figsize=(w, h), dpi=d, sharex=True)
        tsd = [ t for t in range(len(df2_single.index)) ]
        tusd = 1
        lusd = 1
        tsd_ticks = tsd[::tusd]
        tsd_lbl = [ t.strftime('%H:%M') for t in df2_single.index ]
        tsd_lbl = tsd_lbl[::lusd]
        ax = axs[0]
        ax.plot(tsd, df1_single.values, color='C0', label='Sim data')
        ax.plot(tsd, df2_single.values, color='red', label='Viasat UP')

        ax.set_ylabel('Data', color="k")
        ax.grid()
        ax.legend(loc='upper left')

        ax1= axs[1]
        if norm: label_txt=f'L2 - Diff on Normalize curves'
        else: label_txt=f"L2 -Diff"
        ax1.set_ylim(0, 0.05)
        ax1.plot(tsd, l2_diff, color='k', label='L2 diff')
        ax1.set_ylabel(label_txt, color="k")
        ax1.grid()
        ax1.legend(loc='upper left')
        ax1.set_xlabel('Time (H:M)')
        ax1.set_xticks(tsd_ticks)
        ax1.set_xticklabels(tsd_lbl, rotation=45)

        single_save = f'{save_folder}/cluster_analysis'
        if not os.path.exists(single_save): os.makedirs(single_save)
        set_date_save = f'From ' + str(self.startdate_sim).split(' ')[0] + ' to ' +  str(self.stopdate_sim).split(' ')[0]
        fig_tit = f"{single_save}/L2_dist_cid_{col}.png"
        plt.suptitle(f'Polyline {col}\n{set_date_save}')
        fig.savefig(fig_tit)
        plt.close()
        plt.clf() 

        print(f'  Image saved in {os.path.abspath(fig_tit)}')

if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--cfg', help='prepare config file', required=True)
  parser.add_argument("-l", '--local', help='select area', choices=['montagna', 'imola', 'faenza', 'forli', 'cesena'])
  parser.add_argument("-p", "--polycid", help="list of poly cid to filter plot output",  nargs='+', default=[])
  parser.add_argument("-t", "--test_mode", help="test developer mode", action='store_true')
  args = parser.parse_args()

  with open(args.cfg) as cfgfile:
    config = json.load(cfgfile)

  year = config['year']
  if year == '2021':viasatfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'viasat_20210628_20210705_timed_fluxes.csv')
  if year == '2020':viasatfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'viasat_20200210_20200218_timed_fluxes.csv')

  ## Saving Folders
  outdir = config['outdir']
  outdir = os.path.join(outdir, f'{year}')
  if not os.path.exists(outdir): os.makedirs(outdir)

  save_folder = f'{outdir}/{args.local}'
  if not os.path.exists(save_folder): os.makedirs(save_folder)

  save_penetrazione = f'{save_folder}/penetrazione'
  if not os.path.exists(save_penetrazione): os.makedirs(save_penetrazione)

  ## Carto File
  cartofile = config["carto"]
  carto = gpd.read_file(cartofile)
  carto = carto.set_index('poly_cid')
  center_coords = [44.176684, 12.151647]    # Forli-Cesena coord.

  year = config['year']
  if year == '2021':viasatfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'viasat_20210628_20210705_timed_fluxes.csv')
  if year == '2020':viasatfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_viasat', 'viasat_20200210_20200218_timed_fluxes.csv')

  if args.local:
    poly_list = config['city'][args.local]
  else:
    poly_list = args.polycid

  v = viasat()

  viasat_dataframe = v.viasat_builder(viasatfile)
  uniq_dataframe = v.uniq_builder(poly_list, year)
  comparative_analysis = v.penetrazione(carto)
  try:
    geoloc_penetrazione = v.geo_pen(carto)
  except Exception as e:
    print("Error: ", e)
  norm_analysis = v.norm_analysis(args.test_mode)
  if args.local is None: 
    log_cluster_analysis = v.cluster_analysis('Log_')
    l2_diff = v.L2_diff()
