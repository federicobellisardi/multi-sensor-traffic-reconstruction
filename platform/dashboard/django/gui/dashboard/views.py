from django.shortcuts import render, reverse
from django.http import JsonResponse, HttpResponse, HttpResponseNotFound, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from django.utils import timezone
from django.shortcuts import redirect
from matplotlib.style import context

from requests import post, get
import time

import pandas as pd
import json
from matplotlib import cm
from matplotlib.colors import to_hex, rgb2hex
from datetime import timedelta
import numpy as np

from .models import Simulation
from .utils import status_update_thread

from dashboard.utils import carto
from mtsdata.utils import mts

from gui.common import df_to_html, get_colors

import threading
import logging
logger = logging.getLogger('dashboard')

# Create your views here.
@login_required
def submit_view(request):
	try:
		url = f'http://{settings.SIMWS_BASEURL}'
		r = get(url)
		engine_ver = r.json()['version']
	except Exception as e:
		engine_ver = f'error'

	context = {
		'engine_ver' : engine_ver,
	}
	return render(request, 'dashboard/simulation_submit.html', context)

@login_required
def sim_post(request):
	try:
		sim_uid = None

		if request.method == 'POST':
			url = f'http://{settings.SIMWS_BASEURL}/sim'
			# print(url)
			r = post(url, data=request.body, headers=request.headers)
			# print(r)

			if r.status_code == 200:
				body=json.loads(request.body)
				# print(body)
				ret = r.json()
				#print(ret)
				sim_uid = ret['sim_uid']
				ret['status_url'] = reverse('dashboard:sim_status', kwargs={'sim_uid':sim_uid})

				startd = parse_datetime(body['start_date'])
				startd = make_aware(startd)
				stopd = parse_datetime(body['stop_date'])
				stopd = make_aware(stopd)

				sim = Simulation(
					sim_id=sim_uid,
					submitted_by=request.user,
					submitted_time=timezone.now(),
					status='pending',
					start_date=startd,
					stop_date=stopd,
				)
				sim.save()

				if request.user.username == 'provincia_forli_cesena':
					correction_mode = 'delta_std'
				else:
					correction_mode = 'default'

				x = threading.Thread(target=status_update_thread, args=(sim_uid, startd, correction_mode))
				x.start()
			else:
				ret = {'error' : r.text}
				print(r.json())
		else:
			ret = {'error' : 'method not allowed'}
	except Exception as e:
		print('Exception: ', e)
		ret = {'error' : f'sim post failed : {e}'}
		return JsonResponse(ret)

	response = JsonResponse(ret)
	if not sim_uid is None:
		response.set_cookie('cookie-sim_uid', sim_uid)
	return response

@login_required
def status_get(request,sim_uid):

	try:
		sim = Simulation.objects.get(sim_id=sim_uid)
		ret = {
			'sim_uid': sim_uid,
			'status': sim.status,
			'completion': sim.completion,
			'elapsed': sim.runtime
		}
		response = JsonResponse(ret)
		return response

	except Exception as e:
		print(f'Error in getting status : {e}')
		return HttpResponseNotFound()

@login_required
def geojson_get(request):
	try:
		url = f'http://{settings.SIMWS_BASEURL}/poly'
		r = get(url)
		#print(r)
		#print(r.text)
		ret = r.json()
		return JsonResponse(ret)
	except Exception as e:
		logger.error(f'Poly geojson_get : {e}')
		return HttpResponse('Unable to download geojson', status=500)

# simulations database
@login_required
def simulation_view(request):
	try:
		if request.user.is_superuser:
			df = pd.DataFrame(Simulation.objects.all().values())
		else:
			df = pd.DataFrame(Simulation.objects.filter(submitted_by=request.user).values())
		df = df.fillna({'runtime':-1})
		# print(df)
		df['submitted_by'] = [ User.objects.get(id=i) for i in df.submitted_by_id.values ]
		df['runtime_s'] = [ f'{timedelta(seconds=s)}' if type(s) == int or type(s) == float else 0 for s in df.runtime ]
		df['id'] = [ f'<a href="{reverse("dashboard:sim_detail", kwargs={"sim_id":id})}">{id}</a>' for id in df.id.values ]
		#print(df)
		table_content = df_to_html(df[[
			'id',
			'sim_id',
			'start_date',
			#'stop_date',
			#'submitted_by_id',
			'submitted_by',
			'submitted_time',
			'runtime_s',
			'status',
			#'results_path',
		]])
	except Exception as e:
		logger.error(f'Error in simulation_view : {e}')
		table_content = 'No simulation submitted'

	context = dict(
		table_content=table_content,
	)
	return render(request, 'dashboard/simulation_view.html', context)

@login_required
def simulation_detail(request, sim_id):
	if not request.user.is_superuser:
		try:
			sim = Simulation.objects.filter(submitted_by=request.user).get(id=sim_id)
		except Exception as e:
			logger.error(f'Error in permission : {e}')
			if sim_id.isnumeric():
				return HttpResponseForbidden(f'<h1>Error 403: Permission denied for sim number \'{sim_id}\'</h1>', status=403)
			else:
				return HttpResponseForbidden(f'<h1>Error 403: {e}</h1>', status=403)
	else:
		try:
			sim = Simulation.objects.get(id=sim_id)
		except Exception as e:
			logger.error(f'Error in sim detail: {e}')
			if sim_id.isnumeric():
				return HttpResponseNotFound(f'<h1>Error 404: Unable to find sim number \'{sim_id}\'</h1>', status=404)
			else:
				return HttpResponseNotFound(f'<h1>Error 404: {e}</h1>', status=404)

	try:
		if sim.results_path is not None:
			df = pd.read_csv(sim.results_path, sep=',', parse_dates=True, index_col=['datetime', 'poly_lid'])
			df = df.groupby(level=[0,1])['counter'].sum().to_frame().unstack(level=1)
			# df = df.unstack(level=1)
			df.columns = [ int(pl) for _, pl in df.columns ]

			### hardcode first 10 poly
			df = df[list(df.columns[0:10])]
			import numpy as np
			df['ts'] = df.index.values.astype(np.int64) // 10 ** 9
			df.set_index('ts', inplace=True)

			colors = get_colors(len(df.columns), 'cividis')
			cartodf = carto.get_poly()
			allcarto = [ [ [lat, lon] for lon, lat in poly.coords ] for poly in cartodf.geometry ]
			polydf = carto.get_poly(df.columns)
			shapes = [ [ [lat, lon] for lon, lat in poly.coords ] for poly in polydf.geometry ]
			simres = dict(
				times=[ v for v in df.index ],
				headers=[ f'poly id {c}' for c in df.columns ],
				data=df.values.tolist(),
				colors=colors,
				shapes=shapes,
				carto=allcarto,
			)
		else:
			simres = dict(
				sim=sim,
				times=[],
				headers=[],
				data=[],
				colors=[],
				shapes=[],
				carto=[],
			)
	except Exception as e:
		logger.error(f'Error in simulation_detail : {e}')
		sim = 'No simulation exist'
		simres = 'No simulation detail'
	context = dict(
		sim=sim,
		simres=simres,
	)
	return render(request, 'dashboard/simulation_detail.html', context)

@login_required
def simulation_uid_detail(request, sim_uid=None):
	sim = Simulation.objects.get(sim_id=sim_uid)
	return redirect(reverse('dashboard:sim_detail', kwargs={'sim_id':sim.id}))

@login_required
def carto_view(request):
	cartodf = carto.get_poly()
	allcarto = [ [ [lat, lon] for lon, lat in poly.coords ] for poly in cartodf.geometry ]
	simres = dict(
		carto=allcarto,
	)

	context = dict(
		simres=simres,
	)
	return render(request, 'dashboard/carto.html', context)

@login_required
def simulation_fluxes(request, sim_id):
	try:
		sim = Simulation.objects.get(id=sim_id)
		if sim.results_path is not None:
			df = pd.read_csv(sim.results_path, sep=',', parse_dates=True, index_col=['datetime', 'poly_lid'])
			df = df.groupby(level=[0,1])['counter'].sum().to_frame().unstack(level=1).sum().to_frame()
			df = df.rename(columns={0:'counter'})
			df = df.droplevel(level=0)
			dict_counter = {i:j for i,j in zip (df.index, df.counter)}
			quantiles_val = [0.0, 0.20, 0.40, 0.60, 0.80, 0.90, 1.0]
			quantiles = df.counter.quantile(quantiles_val).to_list()
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

			list_color = pd.cut(df.counter, bins=bins, labels=color_scale)
			cartodf = carto.get_poly()
			cartodf['color'] = list_color.to_list()
			cartodf.color.fillna(default_color, inplace=True)
			cartodf['quantile'] = [map_col_quantil[i] for i in cartodf.color]
			cartodf['poly_lid'] = cartodf.index
			cartodf['cnt'] = cartodf['poly_lid'].map(dict_counter)
			cartodf.sort_values(by='quantile', inplace=True)
			center = [42, 11]
			import folium
			m = folium.Map(location=center, control_scale=True)
			layerlabel = '<span style="color: {col};">{txt}</span>'
			import warnings
			warnings.filterwarnings("ignore")
			for qval, grp in cartodf.groupby('quantile'):
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
						color=col,
						popup=folium.Popup(f'<p>Poly cid: <strong>{row.poly_cid}</strong></p><p>Poly lid: <strong>{row.poly_lid}</strong></p><p>Bound coord : <strong>{begin} - {end}</strong></p>', show=False, sticky=True),
						tooltip=folium.Tooltip(f'<p>Poly cid: <strong>{row.poly_cid}</strong></p><p>Simulation counter: <strong>{round(row.cnt)}</strong></p>'),
					)
					flayer_sel.add_child(pol)
				m.add_child(flayer_sel)

			folium.map.LayerControl(collapsed=False).add_to(m)
			sw = min([ [ [lat, lon] for lon, lat in poly.coords ] for poly in cartodf.geometry ])
			ne = max([ [ [lat, lon] for lon, lat in poly.coords ] for poly in cartodf.geometry ])
			m.fit_bounds([ [sw], [ne] ])

			html_string = m._repr_html_()

			simflux = dict(
				html_string=html_string,
				)

		else:
			sim = sim
			simflux = dict(
				html_string=' ',
			)

	except Exception as e:
		logger.error(f'Error in simulation fluxes : {e}')
		sim = 'No simulation exist'
		simflux = 'No simulation detail'

	context = dict(
		sim=sim,
		simflux=simflux,
	)
	return render(request, 'dashboard/simulation_fluxes.html', context)

@login_required
def result_csv(request, sim_id):
	try:
		sim_folder = f'{settings.SIM_RESULT_DIR}/sim_{sim_id}.csv'
		sim_df = pd.read_csv(sim_folder, sep=';')
	except Exception as e:
		logger.error(f'Error in result_csv : {e}')
		sim = 'No simulation exist'
		sim_df = 'No Data'

	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = f'attachment; filename={sim_id}.csv'
	
	sim_df.to_csv(path_or_buf=response,sep=';',index=False)
	return response

# dev
@login_required
def view_playground(request):
	# generate data
	data = mts.nomecomingsoon()

	# render page
	context = dict(data=str(data))
	return render(request, 'dashboard/playground.html', context)

