#! /usr/bin/env python3

import os
import pandas as pd
import geopandas as gpd
import warnings
from shapely.errors import ShapelyDeprecationWarning

# project root: this repository unless COVID_HEP_DIR points to another layout
COVID_HEP = os.environ.get('COVID_HEP_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

def output_forli(df):
	file_name = os.path.join(COVID_HEP, 'data', 'forli_map.csv')
	df_dom = pd.read_csv(file_name, sep=';',encoding='latin-1')
	df_dom = df_dom.set_axis(['SP', 'nome_strada','tratto', 'key_strade','poly_start', 'poly_stop', 'forli_lon_lat_start', 'forli_lon_lat_stop'], axis=1, inplace=False)
	
	df_dom['forli_start'] = df_dom.forli_lon_lat_start.str.split(',').apply(lambda x: ','.join(x[::-1]))
	df_dom['forli_stop'] = df_dom.forli_lon_lat_stop.str.split(',').apply(lambda x: ','.join(x[::-1]))
	df_dom = df_dom[['SP', 'nome_strada','tratto','key_strade','poly_start', 'poly_stop', 'forli_start', 'forli_stop']]
	
	geojson_path = os.path.join(COVID_HEP, 'vars', 'extra')
	geojson_file = f'{geojson_path}/er-carto.geojson'
	geofile = gpd.read_file(geojson_file)

	warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
	lid_match = []
	for i, row in geofile.iterrows():
		start_coord, end_coord = row.geometry.boundary
		begin = (str(start_coord).split(' ',1)[1])[1:-1]
		begin = begin.split(' ')
		begin = ' '.join(reversed(begin)).replace(' ',', ')
		end = (str(end_coord).split(' ',1)[1])[1:-1]
		end = end.split(' ')
		end = ' '.join(reversed(end)).replace(' ',', ')
		lid_match.extend([[row.poly_cid, row.poly_lid, begin, end]])
	
	df_lid = pd.DataFrame(lid_match, columns=['poly_cid', 'poly_lid', 'poly_start', 'poly_stop'])

	ls_more = []
	for j, row in df_dom.iterrows():
		r = df_lid.loc[df_lid['poly_start'] == row.poly_start]
		for k, inner_rows in r.iterrows():
			s = df_lid.loc[df_lid['poly_start'] == inner_rows.poly_stop]
			for l, check_rows in s.iterrows(): 
				if row.poly_stop == check_rows.poly_stop:
					ls_more.append([inner_rows.poly_cid, inner_rows.poly_lid, row.poly_start, check_rows.poly_stop])
					ls_more.append([check_rows.poly_cid, check_rows.poly_lid, row.poly_start, check_rows.poly_stop])
	
	df_lid_more = pd.DataFrame(ls_more, columns=['poly_cid', 'poly_lid', 'poly_start', 'poly_stop'])
	df_lid_more = df_lid_more.drop_duplicates()
	
	df_tot = pd.concat([df_lid, df_lid_more])
	df_tot = df_tot.reset_index(drop=True)
	merged_df = pd.merge(df_dom, df_tot, on=['poly_start', 'poly_stop'])
	merged_df = merged_df[['SP', 'nome_strada','tratto','key_strade','poly_lid', 'poly_cid', 'poly_start', 'poly_stop','forli_start','forli_stop']]
	merged_df = merged_df.sort_values(by=['SP'])
	merged_df = merged_df[['SP', 'nome_strada','tratto','key_strade','poly_lid', 'poly_cid']]

	forli_df = pd.merge(merged_df, df, on=['poly_lid'])
	forli_df = forli_df[['SP','nome_strada','tratto','key_strade','poly_lid','datetime','counter_min','counter_max']]

	return forli_df
