#! /usr/bin/env python3

import matplotlib.pyplot as plt
import pandas as pd
import glob
import json
import os
import re
import requests
import pytz
from datetime import date, datetime

class get_coils():

  def __init__(self):
    self.leap_year = 2000
    self.url = 'https://datacatalog.regione.emilia-romagna.it/catalogCTA/api/3/action/package_show?id=sistema-mts-flussi-di-traffico-al-quarto-d-ora'
    self.data_folder = os.path.join(os.environ['WORKSPACE'],'covid_hep', 'data')
    self.anagrafica = pd.DataFrame()
    self.MTS_barriers = pd.DataFrame(columns = ['Description', 'ID', 'Lat', 'Lon', 'PRO'])
    
    self.short_fmt = '%y%m%d-%H%M%S'
    self.date_fmt = '%Y-%m-%d %H:%M:%S'


  def get_season(self, t):
    leap_year = self.leap_year
    seasons = [('winter', (date(leap_year,  1,  1),  date(leap_year,  3, 20))),
                    ('spring', (date(leap_year,  3, 21),  date(leap_year,  6, 20))),
                    ('summer', (date(leap_year,  6, 21),  date(leap_year,  9, 22))),
                    ('autumn', (date(leap_year,  9, 23),  date(leap_year, 12, 20))),
                    ('winter', (date(leap_year, 12, 21),  date(leap_year, 12, 31)))]
    if isinstance(t, datetime): t = t.date()
    t = t.replace(year=leap_year)
    return next(season for season, (start, end) in seasons if start <= t <= end)

  def dms_to_dd(self, dms_str):
    parts = re.split('[^\d.]+', dms_str)
    degrees = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    decimal_degrees = degrees + minutes/60 + seconds/3600
    return decimal_degrees

  def standard_format(self, wdir):
    try:
      data_string = json.dumps({'id': 'data-explorer'})
      url = self.url
      headers = {'Content-Type': 'application/json'}
      response = requests.post(url, data=data_string, headers=headers, timeout=300)
      assert response.status_code == 200
      response_dict = response.json()
      assert response_dict['success'] is True
      results = response_dict['result']['resources']
      filtered_results = [result for result in results if result.get('format') == 'CSV']
      for result in filtered_results:
        url_csv = result['url']
        file = url_csv.split('/')[-1].split('.')[0].replace(' ', '_')
        if file == 'V_OPD_ADT_APP_DIRMAR':
          continue
          dfmeta = pd.read_csv(url_csv, encoding = "utf-8", sep = ',')
          dfmeta = dfmeta.rename(columns={'APP_ID':'Postazione', 'DIRMAR_COD': 'Direzione Marcia'})
          dfmeta['APP_LATITUDINE']  = dfmeta['APP_LATITUDINE'].apply(get_coils.dms_to_dd)
          dfmeta['APP_LONGITUDINE'] = dfmeta['APP_LONGITUDINE'].apply(get_coils.dms_to_dd)
          self.anagrafica = dfmeta.copy()
          MTS_barriers = dfmeta.drop_duplicates(subset=['Postazione'])
          MTS_barriers = MTS_barriers.rename(columns={'Postazione':'Description', 'APP_LATITUDINE':'Lat', 'APP_LONGITUDINE':'Lon', 'PROV_COD':'PRO'})
          MTS_barriers['ID'] = MTS_barriers['Description']
          MTS_barriers  = MTS_barriers[['Description', 'ID', 'Lat', 'Lon', 'PRO']] 
          self.MTS_barriers = MTS_barriers
          outfile = f'{self.data_folder}/er_barriers_{date.today().strftime("%Y%m%d")}.csv'
          if os.path.exists(outfile): continue
          MTS_barriers.to_csv(outfile, sep=';', index=False)

        elif file == 'V_OPD_ADT_VEI_CLASSE':
          print(f'CLASS file TO PROCESS')
        else:
          try:
            url_csv = url_csv.replace(' ', '%20')
            flows_df = pd.read_csv(url_csv,  sep=',', usecols = [1,2,3])
            flows_df['Data'] = flows_df['Anno'].astype(str) + '-' + flows_df['Mese'].astype(str)
            flows_df['Data'] = pd.to_datetime(flows_df['Data'], format='%Y-%m')
            flows_df = flows_df.drop(columns=["Anno", "Mese"])
            flows_df = flows_df.sort_values(by='Data', ascending=False).iloc[:24]
            for _, row in flows_df.iterrows():
              source = row.URL
              df = pd.read_csv(source, header=[0], sep=',')
              df.rename(columns={'APP_ID':'APPARATO', 'DIRMAR_COD':'CORSIA', 'NUM_TRANSITI' : 'COUNT(*)', 'VEI_ID':'Classe Veicolo ID'},inplace=True)
              df['UTC_Datetime'] = pd.to_datetime(df['GIO_ID'].astype(str) + ' ' + df['HHMI_ID'].astype(str), format='%Y%m%d %H:%M')#.dt.tz_localize('Europe/Berlin', ambiguous=True).dt.tz_convert('UTC')
              df = df[df['Classe Veicolo ID'] == 2]
              df['GIORNO_ORA'] = df['UTC_Datetime'].dt.strftime('%Y-%m-%d %H')
              df = df.sort_values(by='GIORNO_ORA', axis=0)
              df['INTERVALLO'] = [i[3:5] for i in df['HHMI_ID']]
              df['TIPO_VEICOLO'] = 2
              print(df)
              start_date = df.UTC_Datetime.min().date()
              stop_date = df.UTC_Datetime.max().date()
              outfile = f'{wdir}/{start_date.strftime("%Y%m%d")}_{stop_date.strftime("%d")}.mdb.csv'
              if os.path.exists(outfile): continue
              df.to_csv(outfile, sep=';', index=False, columns=['GIORNO_ORA','INTERVALLO','APPARATO','CORSIA','TIPO_VEICOLO','COUNT(*)'])      
          except Exception as e:
            print(f'Exception {e}')
    except Exception as e:
      print(f'Exception {e}')

  def convert(self, wdir, odir):
    data_folder = self.data_folder
    coilsfiles = glob.glob(f'{wdir}/*.mdb.csv')
    outdir = odir
    dfc = pd.DataFrame()
    for i, cf in enumerate(coilsfiles):
      df = pd.read_csv(cf, sep=';', engine='c')
      df['datetime'] = pd.to_datetime([ f'{go}:{inter:02}:00' for go, inter in df[['GIORNO_ORA', 'INTERVALLO']].values ])
      dfc = dfc.append(df)

    totdata = len(dfc)
    dfc = dfc[ dfc.TIPO_VEICOLO < 11 ]
    print(f'Total record {totdata}, valid {len(dfc)} ({len(dfc)/totdata:.4f})')

    dfc.datetime = dfc.datetime.dt.tz_localize('utc')
    dfc['Direzione'] = dfc['CORSIA']

    dfc = dfc.groupby(['datetime', 'APPARATO', 'Direzione']).agg({'COUNT(*)':'sum'})
    dfc = dfc.unstack(level=[1,2])
    dfc.columns = [ f'{c}_{d}' for _,c,d in dfc.columns ]

    df_last_year = dfc[dfc.index.year == datetime.now().year - 1]
    df_this_year = dfc[dfc.index.year == datetime.now().year]

    if df_this_year.empty:
      df_last_year = dfc[dfc.index.year == datetime.now().year - 2]
      df_this_year = dfc[dfc.index.year == datetime.now().year - 1]

    df_list = [df_last_year, df_this_year]
    for df in df_list:
      start = df.index.min().strftime(self.short_fmt)
      stop = df.index.max().strftime(self.short_fmt)
      timetag = f'{start}_{stop}'
      outcsv = f'{outdir}/coils_table_{timetag}.csv'
      df.to_csv(outcsv, sep=';', index=True)
      print(f'[coils_model] Coils table saved to : {outcsv}')

      df['wday'] = [ t.strftime('%a') for t in df.index ]
      df['wday_n'] = [ t.strftime('%w') for t in df.index ]
      df['time'] = [ t.strftime('%H:%M') for t in df.index ]
      df['season'] = [ get_coils.get_season(t.date()) for t in df.index ]
      df_ave = df.groupby(['wday', 'wday_n', 'time', 'season']).mean().reset_index().sort_values(by=['wday_n', 'time'])
      df_std = df.groupby(['wday', 'wday_n', 'time', 'season']).std().reset_index().sort_values(by=['wday_n', 'time'])

      outcsv_ave = f'{outdir}/coils_ave_{timetag}.csv'
      df_ave.to_csv(outcsv_ave, sep=';', index=False)
      print(f'[coils_model] Daily average saved to : {outcsv_ave}')

      outcsv_std = f'{outdir}/coils_std_{timetag}.csv'
      df_std.to_csv(outcsv_std, sep=';', index=False)
      print(f'[coils_model] Daily std saved to : {outcsv_std}')


  def geocoil(self, carto_file):
    import folium
    import geopandas as gpd
    import warnings

    coils = self.MTS_barriers
    carto = gpd.read_file(carto_file)
    center = carto.to_crs(epsg=3003).centroid.to_crs(epsg=4326)
    center = [ center.y.mean(), center.x.mean() ]
    m = folium.Map(location=center, control_scale=True)
    warnings.filterwarnings("ignore")#, category=ShapelyDeprecationWarning)

    layerlabel = '<span style="color: {col};">{txt}</span>'
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

    folium.map.LayerControl(collapsed=True).add_to(m)
    e, s, w, n = carto.total_bounds
    m.fit_bounds([ [s,w], [n,e] ])
    file_name = f'coils_location_{date.today().strftime("%Y%m%d")}'
    html_file = f'{coils_folder}/{file_name}.html'
    m.save(html_file)
    print(f'File saved: {os.path.abspath(html_file)} ')


if __name__ == '__main__':
  pd.options.mode.chained_assignment = None
  
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-g', '--geoloc', help='geolocalize coils', action='store_true')
  args = parser.parse_args()

  cartofile =  os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'data', 'carto.geojson')

  mdb_folder = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_spire', 'mdb')
  if not os.path.exists(mdb_folder): os.mkdir(mdb_folder)  
  
  coils_folder = os.path.join(os.environ['WORKSPACE'], 'covid_hep', 'work_spire', 'coils_table')
  if not os.path.exists(coils_folder): os.mkdir(coils_folder)

  get_coils =  get_coils()

  standard_format = get_coils.standard_format(mdb_folder)
  print(f'mdb files saved on {mdb_folder}')

  convert = get_coils.convert(mdb_folder, coils_folder)

  if args.geoloc: get_coils.geocoil(cartofile)