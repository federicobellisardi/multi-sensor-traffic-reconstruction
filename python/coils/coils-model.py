#! /usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import argparse
import glob
import json
import os
import re
import requests
import sys
import pytz
import locale
from datetime import datetime
from collections import defaultdict

class coils_model():

  def __init__(self):
    self.short_fmt = '%y%m%d-%H%M%S'
    self.date_fmt = '%Y-%m-%d %H:%M:%S'
    self.tz_rome = pytz.timezone('Europe/Rome')

  def standard_format(self, wdir, mode):
    if mode == '20ago':
      coilsfiles = glob.glob(f'{wdir}/*.xlsx')
      for cfile in coilsfiles:
        sheets = pd.read_excel(cfile, None)
        for stag, df in sheets.items():
          df.rename(columns={'Postazione':'APPARATO', 'Direzione Marcia':'CORSIA'},inplace=True)
          df['COUNT(*)'] = df.iloc[:,5:15].sum(axis=1)
          df['Giorno'] = pd.to_datetime(df['Giorno'], format='%d/%m/%Y')
          df['Giorno'] = df['Giorno'].dt.strftime('%Y-%m-%d')
          df['Datetime'] = df['Giorno'] + ' '+df['Ora']
          df['UTC_Datetime'] = pd.to_datetime(df['Datetime'], format='%Y-%m-%d %H:%M').dt.tz_localize('Europe/Berlin').dt.tz_convert('UTC')
          df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
          df = df.sort_values(by='GIORNO_ORA', axis=0)
          df['INTERVALLO'] = [i[3:5] for i in df.Ora]
          df['TIPO_VEICOLO'] = 2

          start_date = df.UTC_Datetime.min().date()
          stop_date = df.UTC_Datetime.max().date()
          outfile = f'{wdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
          df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])

    elif mode == '30apr':
      coilsfiles = glob.glob(f'{wdir}/*.csv')
      for cfile in coilsfiles:
        df = pd.read_csv(cfile)
        df['Giorno'] = df['Giorno'].str.replace('Giu','Jun')
        df['Giorno'] = df['Giorno'].str.replace('Dic','Dec')
        df['Giorno'] = df['Giorno'].str.replace('Gen','Jan')

        df.rename(columns={'Postazione':'APPARATO', 'Direzione Marcia':'CORSIA'},inplace=True)
        df['COUNT(*)'] = df.iloc[:,5:15].sum(axis=1)
        df['Giorno'] = pd.to_datetime(df['Giorno'], format='%d %b %Y')
        df['Giorno'] = df['Giorno'].dt.strftime('%Y-%m-%d')
        df['Datetime'] = df['Giorno'] + df['1/4 h [HH-MM]']
        df['UTC_Datetime'] = pd.to_datetime(df['Datetime'], format='%Y-%m-%d %H:%M').dt.tz_localize('Europe/Berlin').dt.tz_convert('UTC')
        df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
        df = df.sort_values(by='GIORNO_ORA', axis=0)
        df['INTERVALLO'] = [i[4:6] for i in df['1/4 h [HH-MM]']]
        df['TIPO_VEICOLO'] = 2

        start_date = df.UTC_Datetime.min().date()
        stop_date = df.UTC_Datetime.max().date()
        outfile = f'{wdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
        df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])

    elif mode == '31ott':
      coilsfiles = glob.glob(f'{wdir}/*.csv')
      for cfile in coilsfiles:
        df = pd.read_csv(cfile)
        df.rename(columns={'Postazione':'APPARATO', 'Direzione Marcia':'CORSIA'},inplace=True)
        df['COUNT(*)'] = df.iloc[:,5:15].sum(axis=1)
        locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
        df['Giorno'] = pd.to_datetime(df['Giorno'], format='%d %b %Y')
        df['Giorno'] = df['Giorno'].dt.strftime('%Y-%m-%d')
        df['Datetime'] = df['Giorno'] + df['1/4 h [HH-MM]']
        df['UTC_Datetime'] = pd.to_datetime(df['Datetime'], format='%Y-%m-%d %H:%M').dt.tz_localize('Europe/Berlin', ambiguous=True).dt.tz_convert('UTC')
        df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
        df = df.sort_values(by='GIORNO_ORA', axis=0)
        df['INTERVALLO'] = [i[4:6] for i in df['1/4 h [HH-MM]']]
        df['TIPO_VEICOLO'] = 2

        start_date = df.UTC_Datetime.min().date()
        stop_date = df.UTC_Datetime.max().date()
        outfile = f'{wdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
        print(f'File saved on {outfile}')
        df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])

    elif mode == 'new_output':
      '''
      New Output Sample

      CRITERIO VALIDITA Postazione  Giorno         1/4 h[HH-MM]  GG  Direzione Marcia  Classe Veicolo ID     Classe Veicolo     Num Transiti [Aggr]
      TGM_GG_VALIDI         6       21 Giu 2022    0:30          21         0                2              Auto e monovolume          1
      '''
      coilsfiles = glob.glob(f'{wdir}/*.csv')
      for cfile in coilsfiles:
        df = pd.read_csv(cfile)
        df.rename(columns={'Postazione':'APPARATO', 'Direzione Marcia':'CORSIA', 'Num Transiti [Aggr]' : 'COUNT(*)'},inplace=True)
        df['Giorno'] = df['Giorno'].str.replace('Giu','Jun')
        df['Giorno'] = df['Giorno'].str.replace('Dic','Dec')
        df['Giorno'] = df['Giorno'].str.replace('Gen','Jan')
        df['Giorno'] = df['Giorno'].str.replace('Ott','Oct')


        df['Giorno'] = pd.to_datetime(df['Giorno'], format='%d %b %Y')
        df['Giorno'] = df['Giorno'].dt.strftime('%Y-%m-%d')
        df['Datetime'] = df['Giorno'] + df['1/4 h [HH-MM]']

        df = df[df['Classe Veicolo ID'] == 2]

        df['UTC_Datetime'] = pd.to_datetime(df['Datetime'], format='%Y-%m-%d %H:%M').dt.tz_localize('Europe/Berlin', ambiguous=True).dt.tz_convert('UTC')
        df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
        df = df.sort_values(by='GIORNO_ORA', axis=0)
        df['INTERVALLO'] = [i[4:6] for i in df['1/4 h [HH-MM]']]
        df['TIPO_VEICOLO'] = 2

        start_date = df.UTC_Datetime.min().date()
        stop_date = df.UTC_Datetime.max().date()
        outdir = 'mdb'
        if not os.path.exists(outdir): os.makedirs(outdir)

        outfile = f'{outdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
        df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])      
        print(f'File saved on {outfile}')
    elif mode == 'api':
      data_string = json.dumps({'id': 'data-explorer'})
      url = 'https://datacatalog.regione.emilia-romagna.it/catalogCTA/api/3/action/package_show?id=sistema-mts-flussi-di-traffico-al-quarto-d-ora'
      headers = {'Content-Type': 'application/json'}
      response = requests.post(url, data=data_string, headers=headers)
      assert response.status_code == 200
      response_dict = response.json()
      assert response_dict['success'] is True
      results = response_dict['result']['resources']
      filtered_results = [result for result in results if result.get('format') == 'CSV']
      for result in filtered_results:
        url_csv = result['url']
        df = pd.read_csv(url_csv, header=[0], sep=',')
        df.rename(columns={'APP_ID':'APPARATO', 'DIRMAR_COD':'CORSIA', 'NUM_TRANSITI' : 'COUNT(*)', 'VEI_ID':'Classe Veicolo ID'},inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['GIO_ID'].astype(str) + ' ' + df['HHMI_ID'].astype(str), format='%Y%m%d %H:%M')#.dt.tz_localize('Europe/Berlin', ambiguous=True).dt.tz_convert('UTC')
        df = df[df['Classe Veicolo ID'] == 2]

        df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
        df = df.sort_values(by='GIORNO_ORA', axis=0)
        df['INTERVALLO'] = [i[3:5] for i in df['HHMI_ID']]
        df['TIPO_VEICOLO'] = 2
        start_date = df.UTC_Datetime.min().date()
        stop_date = df.UTC_Datetime.max().date()
        outdir = 'mdb'
        if not os.path.exists(outdir): os.makedirs(outdir)
        outfile = f'{outdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
        df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])      
        print(f'File saved on {outfile}')        

  def convert(self, wdir):
    data_folder = os.path.join(os.environ['WORKSPACE'],'covid_hep', 'data')
    coilsfiles = glob.glob(f'{wdir}/*.mdb.csv')
    outdir = 'coils_file'
    if not os.path.exists(outdir): os.makedirs(outdir)
    # read metadata
    file_anagrafica = glob.glob(f'{data_folder}/Anagrafica*.csv')[0]
    print(file_anagrafica)
    if file_anagrafica == 'Anagrafica_20211030.csv':
      dfmeta = pd.read_csv(file_anagrafica, encoding = "ISO-8859-1", sep = ',', skiprows=[0])
    else:
      dfmeta = pd.read_csv(file_anagrafica, encoding = "ISO-8859-1", sep = ';', skiprows=[0])

    dir_map = { (cid, lane) : dire for cid, lane, dire in dfmeta[['Postazione', 'Corsia', 'Direzione Marcia']].values }
    corsie_grp = dfmeta.groupby('n. Corsie').count()
    # print(corsie_grp)
    # print(dir_map)

    dfc = pd.DataFrame()
    for i, cf in enumerate(coilsfiles):
      print(f'[coils_model] Processing : {cf}')
      df = pd.read_csv(cf, sep=';', engine='c')
      df['datetime'] = pd.to_datetime([ f'{go}:{inter:02}:00' for go, inter in df[['GIORNO_ORA', 'INTERVALLO']].values ])
      # print(df.columns)
      dfc = dfc.append(df)
      #if i>0: break

    # filter out errors
    totdata = len(dfc)
    dfc = dfc[ dfc.TIPO_VEICOLO < 11 ]
    print(f'Total record {totdata}, valid {len(dfc)} ({len(dfc)/totdata:.4f})')

    # aggregate
    dfc.datetime = dfc.datetime.dt.tz_localize('utc') # problems with non-existent timestamps...
    dfc['Direzione'] = [ dir_map[(cid, lane)] for cid, lane in dfc[['APPARATO', 'CORSIA']].values ]
    dfc = dfc.groupby(['datetime', 'APPARATO', 'Direzione']).agg({'COUNT(*)':'sum'})
    dfc = dfc.unstack(level=[1,2])
    dfc.columns = [ f'{c}_{d}' for _,c,d in dfc.columns ]
    # dfc_22 = dfc.loc[dfc.index.date == pd.to_datetime('2022-06-22') ]
    # dump tables
    start = dfc.index.min().strftime(self.short_fmt)
    stop = dfc.index.max().strftime(self.short_fmt)
    timetag = f'{start}_{stop}'
    outcsv = f'{outdir}/coils_table_{timetag}.csv'
    dfc.to_csv(outcsv, sep=';', index=True)
    print(f'[coils_model] Coils table saved to : {outcsv}')

    # compute and dump daily average
    dfc['wday'] = [ t.strftime('%a') for t in dfc.index ]
    dfc['wday_n'] = [ t.strftime('%w') for t in dfc.index ]
    dfc['time'] = [ t.strftime('%H:%M') for t in dfc.index ]
    dfc_ave = dfc.groupby(['wday', 'wday_n', 'time']).mean().reset_index().sort_values(by=['wday_n', 'time'])
    dfc_std = dfc.groupby(['wday', 'wday_n', 'time']).std().reset_index().sort_values(by=['wday_n', 'time'])

    outcsv_ave = f'{outdir}/coils_ave_{timetag}.csv'
    dfc_ave.to_csv(outcsv_ave, sep=';', index=False)
    print(f'[coils_model] Daily average saved to : {outcsv_ave}')

    outcsv_std = f'{outdir}/coils_std_{timetag}.csv'
    dfc_std.to_csv(outcsv_std, sep=';', index=False)
    print(f'[coils_model] Daily std saved to : {outcsv_std}')


  def plot(self, tablecsv, avecsv, coilsfilter, start_date='', stop_date=''):
    dft = pd.read_csv(tablecsv, sep=';', index_col=0, parse_dates=True)
    dfa = pd.read_csv(avecsv, sep=';', index_col=[0,1,2])

    # time crop, filter and merge ave
    start = dft.index.min() if start_date == '' else pd.to_datetime(start_date + 'CET', format=self.short_fmt + '%Z')
    stop = dft.index.max() if stop_date == '' else pd.to_datetime(stop_date + 'CET', format=self.short_fmt + '%Z')
    dft = dft[ (dft.index >= start) & (dft.index < stop) ]

    cols = [ c for c in dft.columns if any([ re.match(f, c) != None for f in coilsfilter ]) ] if len(coilsfilter) else dft.columns
    cols_ave = [ f'{c}_ave' for c in cols ]
    dft = dft[cols]
    dfa = dfa[cols].reset_index()

    # print(dft)
    # print(dfa)

    dft['wday'] = [ t.strftime('%a') for t in dft.index ]
    dft['wday_n'] = [ int(t.strftime('%w')) for t in dft.index ]
    dft['time'] = [ t.strftime('%H:%M') for t in dft.index ]
    # print(dft)

    dfm = dft.merge(dfa, how='left', on=['wday','wday_n','time'], suffixes=['', '_ave'])
    dfm = dfm.drop(columns=['wday', 'wday_n', 'time'])
    dfm.index = dft.index
    dfm = dfm.tz_convert('Europe/Rome')
    # print(dfm)

    outdir = 'aveplot'
    if not os.path.exists(outdir): os.mkdir(outdir)

    # plot
    fig, ax = plt.subplots(1,1, figsize=(12,8))
    dfm[cols].plot(ax=ax, style='-o')
    dfm[cols_ave].plot(ax=ax, style='--')
    ax.grid()

    plt.tight_layout()
    fig.subplots_adjust(top=0.9)
    ptitle = f'Coils data for {start} {stop}'
    plt.suptitle(ptitle, y=0.98)

    timetag = f'{start.strftime(self.short_fmt)}_{stop.strftime(self.short_fmt)}'
    base = 'coils_data_ave'
    plt.savefig(f'{outdir}/{base}_{timetag}.png')
    plt.close()

  def generate_tt(self):
    return 1

  def geoplot(self, dirmapfile=None):
    import geopandas as gpd
    import folium

    coilsgeodata = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
    coilsdf = pd.read_csv(coilsgeodata, sep=';')
    coilsdf = coilsdf.set_index('ID', drop=False)
    coils = gpd.GeoDataFrame(coilsdf, geometry= gpd.points_from_xy(coilsdf.Lon, coilsdf.Lat))
    coils = coils.set_crs(epsg=4326)
    er_center = coils[['Lat', 'Lon']].mean().values
    print(coils)

    proshapef = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-shapes.geojson')
    proshape = gpd.read_file(proshapef)
    print(proshape)

    outdir = 'htmlmap'
    if not os.path.exists(outdir): os.mkdir(outdir)

    if dirmapfile != None:
      coildir = pd.read_csv(dirmapfile, sep=';', index_col='coil_id', comment='#')
      sel_mask = coils.index.isin(coildir.index)
      coils_sel = coils[ sel_mask ]
      coils_nope = coils[ ~sel_mask ]
      outbase = dirmapfile[:dirmapfile.rfind('.')]
    else:
      coils_sel = pd.DataFrame()
      coils_nope = coils
      outbase = f'{outdir}/map_layers'
    print(f'Coils tot {len(coils)}, selected {len(coils_sel)} ({len(coils_sel)/len(coils):.2f}), nope {len(coils_nope)} ({len(coils_nope)/len(coils):.2f})')

    # layers
    m = folium.Map(location=er_center, control_scale=True, zoom_start=9)
    layerlabel = '<span style="color: {col};">{txt}</span>'
    flayer_sel = folium.FeatureGroup(name=layerlabel.format(col='red', txt='selected coils'))
    for cid, row in coils_sel.iterrows():
      pt = folium.CircleMarker(
        location=[row.Lat, row.Lon],
        radius=5,
        fill_color='red',
        color='red',
        popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
      )
      flayer_sel.add_child(pt)
    flayer_nope = folium.FeatureGroup(name=layerlabel.format(col='blue', txt='coils'))
    for cid, row in coils_nope.iterrows():
      pt = folium.CircleMarker(
        location=[row.Lat, row.Lon],
        radius=5,
        fill_color='blue',
        color='blue',
        popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
      )
      flayer_nope.add_child(pt)
    flayer_pro = folium.FeatureGroup(name=layerlabel.format(col='gray', txt='pro shapes'))
    for cid, row in proshape.iterrows():
      pol = folium.Polygon(
        locations=[ [lat,lon] for lon,lat in row.geometry.exterior.coords],
        fill_color='gray',
        color='gray',
        popup=folium.Popup(f'<p>name <b>{row.PRO_NAME}</b></br>id <b>{row.PRO}</b></p>', show=False, sticky=True),
      )
      flayer_pro.add_child(pol)
    m.add_child(flayer_pro)
    m.add_child(flayer_sel)
    m.add_child(flayer_nope)
    folium.map.LayerControl(collapsed=False).add_to(m)
    e, s, w, n = coils.total_bounds
    m.fit_bounds([ [s,w], [n,e] ])
    m.save(f'{outbase}.html')
    print(f"File saved in {outbase}")

    # coils only
    coils.apply(lambda row: folium.CircleMarker(
      location=[row.Lat, row.Lon],
      radius=5,
      fill_color='purple',
      color='purple',
      popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
    ).add_to(m), axis=1)
    e, s, w, n = coils.total_bounds
    m.fit_bounds([ [s,w], [n,e] ])
    m.save(f'{outdir}/map_coils.html')
    print(f"File saved in {outdir}")

    # coils + polygons
    m = folium.Map(location=er_center, control_scale=True, zoom_start=9)
    proshape.apply(lambda row: folium.Polygon(
      locations=[ [lat,lon] for lon,lat in row.geometry.exterior.coords],
      fill_color='blue',
      color='blue',
      popup=folium.Popup(f'<p>id <b>{row.PRO_NAME}</b></br>name <b>{row.PRO}</b></p>', show=False, sticky=True),
    ).add_to(m), axis=1)
    coils.apply(lambda row: folium.CircleMarker(
      location=[row.Lat, row.Lon],
      radius=5,
      fill_color='purple',
      color='purple',
      popup=folium.Popup(f'coil {row.ID}', show=False, sticky=True),
    ).add_to(m), axis=1)
    e, s, w, n = proshape.total_bounds
    m.fit_bounds([ [s,w], [n,e] ])
    m.save(f'{outdir}/map_coils_shapes.html')
    print(f"File saved in {outdir}")


  def validate(self, validatefile):
    # import coil table csv
    base = validatefile[:validatefile.rfind('.')]
    dfcoils = pd.read_csv(validatefile, sep=';', parse_dates=['datetime'], index_col='datetime', engine='c')
    #print(dfcoils)
    start = dfcoils.index.min()
    stop = dfcoils.index.max()

    # resample by counting to find out missing data
    sampling = '1D'
    stats = dfcoils.resample(sampling).count()
    #print(stats)

    # load coils metadata file
    metafile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
    coilmeta = pd.read_csv(metafile, sep=';')

    # restore missing coil/direction
    all_bar = [ f'{i}_0' for i in coilmeta.ID.values ]
    all_bar.extend([ f'{i}_1' for i in coilmeta.ID.values ])
    for b in all_bar:
      if b not in stats.columns:
        stats[b] = 0

    # consistency check
    # ana_id = set(coilmeta.ID.values)
    # data_id = set([ int(b.split('_')[0]) for b in stats.columns ])
    # print('coil', len(ana_id))
    # print('coil', len(data_id))
    # ana_bar = set(all_bar)
    # data_bar = set([ b for b in stats.columns ])
    # print('bar', len(ana_bar))
    # print('bar', len(data_bar))
    # print('diff ana-data', ana_bar.difference(data_bar))
    # print('diff data-ana', data_bar.difference(ana_bar))

    # select useless coil/direction
    thresh = 0.5
    stats_all = stats.sum(axis=0).to_frame('check')
    max_check = stats_all.check.max()
    mask = stats_all.check < thresh * max_check
    nope = stats_all[ mask ]
    yep = stats_all[ ~mask ]
    print(f'Total directions : {len(stats_all)}')
    print(f'Useless          : {len(nope)} ({len(nope)/len(stats_all):.02f})')
    print(f'Valid            : {len(yep)} ({len(yep)/len(stats_all):.02f})')

    outdir = 'validation'
    if not os.path.exists(outdir): os.mkdir(outdir)

    for pro, df in coilmeta.groupby('PRO'):
      print(f'Validating pro   : {pro} coils {len(df)} ({len(df)/len(coilmeta):.2f})')
      bar_list = [ f'{i}_0' for i in df.ID.values ]
      bar_list.extend([ f'{i}_1' for i in df.ID.values ])
      #print(bar_list)
      coilpro = stats[bar_list].sort_index(axis=1)

      fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 12))
      cnt = coilpro.values
      cnt[ cnt > 0 ] = 1
      color_map = ax.imshow(cnt.T, extent=[0, 1, 0, 1], interpolation='none', vmin=0, vmax=1)
      color_map.set_cmap('plasma')
      #plt.colorbar(color_map, ax=ax)

      dy = 1 / len(coilpro.columns)
      plt.gca().set_yticks([ (n + 0.5)*dy for n in range(len(coilpro.columns))])
      plt.gca().set_yticklabels(coilpro.columns[::-1])

      dx = 1 / len(coilpro.index)
      max_ticks = 20
      plt.gca().set_xticks([ (n + 0.5)*dx for n in range(len(coilpro.index))])
      lbls = [ t.strftime('%Y %b %d %H:%M') for t in coilpro.index]
      if len(lbls) > max_ticks:
        for i in range(len(lbls)):
          if i % (len(lbls) // max_ticks) != 0:
            lbls[i] = ''
      plt.gca().set_xticklabels(lbls, rotation=45, ha='right')

      plt.title(f'Validation {pro} coils ({len(coilpro.columns)/2:.0f}/{len(coilmeta)} - {len(coilpro.columns)/2/len(coilmeta):.2f})\nfor {start} - {stop} @ {sampling} sec')
      plt.tight_layout()
      plt.savefig(f'{outdir}/{base}_{pro}_validate.png')
      plt.close()

  def ranking(self, rankfile):
    # load coils table data
    base = rankfile[:rankfile.rfind('.')]
    dfcoils = pd.read_csv(rankfile, sep=';', parse_dates=['datetime'], index_col='datetime', engine='c')
    #print(dfcoils)
    start = dfcoils.index.min()
    stop = dfcoils.index.max()

    # load coil metadata
    metafile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
    coilmeta = pd.read_csv(metafile, sep=';')
    #print(coilmeta)

    #outdir = 'ranking'
    #if not os.path.exists(outdir): os.mkdir(outdir)

    # do ranking by prov
    sel_all = defaultdict(lambda : pd.DataFrame())
    for pro, df in coilmeta[['ID', 'PRO']].groupby('PRO'):
      print(f'Ranking pro : {pro}')
      bar_list = [ f'{i}_0' for i in df.ID.values ]
      bar_list.extend([ f'{i}_1' for i in df.ID.values ])

      dfpro = dfcoils.copy()
      # add missing coils
      for b in bar_list:
        if b not in dfpro.columns:
          dfpro[b] = 0
      dfpro = dfpro[bar_list].sort_index(axis=1)

      dfpro = dfpro.sum().to_frame('tot')
      dfpro['coil_id'] = [ s.split('_')[0] for s in dfpro.index ]
      dfpro = dfpro.groupby('coil_id').sum()
      #print(dfpro)
      dfpro = dfpro.sort_values(by='tot', ascending=False)
      dfpro['cumul'] = dfpro.tot.cumsum() / dfpro.tot.sum()
      #print(dfpro)

      percentiles = [ 0.5, 0.75, 0.8, 0.95, 1 ]
      quantiles = {}
      for p in percentiles:
        df2 = dfpro[ dfpro.cumul > p ].copy()
        if len(df2):
          perc_tag = df2.index[0]
          perc_idx = dfpro.index.get_loc(perc_tag)
          quantiles[p] = perc_idx
          #print(perc_tag, perc_idx)
        else:
          quantiles[p] = len(dfpro)

      # collect prov selection
      for sel_perc in percentiles:
        sel = dfpro.iloc[:quantiles[sel_perc]]
        sel = pd.DataFrame(
          [ [0, 'IN'] for _ in sel.index],
          index=pd.Index([ f'{u}' for u in sel.index], name='coil_id'),
          columns=['dir_reg', 'dir_carto']
        )
        sel_all[sel_perc] = sel_all[sel_perc].append(sel)
      #print(sel)

      # plot
      fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12, 12))
      colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
      dy = 1 / len(dfpro)
      yticks = [ (n + 0.5)*dy for n in range(len(dfpro))]
      plt.gca().set_yticks(yticks)
      plt.gca().set_yticklabels(dfpro.index[::-1])
      ax.barh(yticks, dfpro.tot.values[::-1], height=0.9*dy, align='center')
      for col, (q,i) in zip(colors[1:], quantiles.items()):
        ax.axhline((len(dfpro) - i) / len(dfpro), ls='--', color=col, label=f'perc {q} coils {i}/{len(dfpro)} ({i/len(dfpro):.2f})')
      ax.set_xlabel('Total counter (all directions)')
      ax.set_ylim([0,1])
      ax.grid()
      ax.legend()
      plt.title(f'{pro} coils ({len(dfpro)}) ranking\nfor {start} - {stop}')
      plt.tight_layout()
      plt.savefig(f'{base}_{pro}_ranking.png')
      plt.close()
      #break

    for sel_perc, sel in sel_all.items():
      sel.to_csv(f'coils-dir-mapping_template_{sel_perc:.2f}.csv', sep=';')
      print(f'Ranking selection thresh {sel_perc} coils : {len(sel)}/{len(coilmeta)} ({len(sel)/len(coilmeta):.2f})')

  def geotag(self):
    """ Annotate repo's barriers.csv with PROV tag"""
    from shapely import geometry
    import geopandas as gpd

    # read coils geodata
    barfile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er_barriers.csv')
    dfbar = pd.read_csv(barfile, sep=';')
    dfbar = dfbar.drop(columns='Description').set_index('ID')
    geometry = [ geometry.Point(xy) for xy in zip(dfbar.Lon, dfbar.Lat) ]
    crs = 'epsg:4326'
    dfbar = gpd.GeoDataFrame(dfbar, crs=crs, geometry=geometry)
    #print(dfbar)

    # read pro shapes
    profile = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'vars', 'extra', 'er-shapes.geojson')
    dfpro = gpd.read_file(profile)
    dfpro = dfpro.set_index('UID')
    #print(dfpro)

    # match coils and pro
    dfbar['PRO'] = 'N/A'
    for bid, brow in dfbar.iterrows():
      for pid, prow in dfpro.iterrows():
        if prow.geometry.contains(brow.geometry):
          #print(f'{bid} sta in {pid}')
          dfbar.loc[bid, 'PRO'] = prow.PRO_NAME
          break
    dfbar = dfbar.reset_index().sort_values(by=['PRO', 'ID']).set_index('ID')#.drop(columns=['Lat', 'Lon', 'geometry'])
    dfbar['PRO'] = dfbar.PRO.str[:2].str.upper()
    dfbar['Description'] = dfbar.index
    dfbar['ID'] = dfbar.index

    #dfbar = dfbar[ dfbar.index.isin(coil_list) ]
    print(dfbar)

    dfbar[['Description', 'ID', 'Lat', 'Lon', 'PRO']].to_csv('geotag.csv', sep=';', index=False)



if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-t', '--tablecsv', help='input .mdb.csv file', default='')
  parser.add_argument('-a', '--avecsv', help='input .mdb.csv file', default='')
  parser.add_argument('-r', '--trange', help='time range like "200101-100000|200101-120000"', default='')
  parser.add_argument('-c', '--coilsid', help='list of coils id to filter out', nargs='+', default=[])
  parser.add_argument('-w', '--workdir', help='directory with coils data .mdb.csv', default='')
  parser.add_argument('-g', '--dogeo', help='generate coils maps', action='store_true')
  parser.add_argument('-dc', '--dircoil', help='coil direction mapping', default=None)
  parser.add_argument('-v', '--validate', help='coils table csv file', default=None)
  parser.add_argument('-gt', '--geotag', help='enable geotag mode', action='store_true')
  parser.add_argument('-rk', '--rank', help='coils table csv file', default=None)
  parser.add_argument('-f', '--format', help='coils raw data format standardization (check the code)', action='store_true')

  args = parser.parse_args()

  cmod = coils_model()

  if args.format:
    # cmod.standard_format('transiti', mode='new_output')
    cmod.standard_format('', mode='api')

  if args.workdir != '':
    cmod.convert(args.workdir)

  if args.tablecsv != '' and args.avecsv != '':
    if args.trange == '':
      start = ''
      stop = ''
    else:
      start, stop = args.trange.split('|')
    cmod.plot(args.tablecsv, args.avecsv, args.coilsid, start, stop)

  if args.dogeo:
    cmod.geoplot(args.dircoil)

  if args.geotag:
    cmod.geotag()

  if args.validate != None:
    cmod.validate(args.validate)

  if args.rank != None:
    cmod.ranking(args.rank)