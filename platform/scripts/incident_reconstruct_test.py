#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import geopandas as gpd
import requests, json, time, hashlib
import numpy as np

ROOT = Path('/home/fede/code/covid_hep')
inc_path = ROOT / 'data' / 'incidenti.csv'
OSM_CACHE_DIR = ROOT / 'article' / 'cache' / 'osm_ways'
OSM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = {'User-Agent':'covid_hep_agent/1.0 (+https://github.com)'}

if not inc_path.exists():
    raise FileNotFoundError(inc_path)
inc = pd.read_csv(inc_path, sep=';') if ';' in open(inc_path).read(2048) else pd.read_csv(inc_path)

def nominatim_bbox_for_admin(region='', province=''):
    q = ', '.join([x for x in [province, region, 'Italy'] if x])
    url = 'https://nominatim.openstreetmap.org/search'
    params = {'q': q, 'format': 'json', 'limit': 1}
    try:
        r = requests.get(url, params=params, headers=USER_AGENT, timeout=30)
        if r.ok and r.json():
            item = r.json()[0]
            bb = [float(x) for x in item.get('boundingbox', [])]
            if len(bb) == 4:
                return bb
    except Exception as exc:
        print('Nominatim error:', exc)
    return None

def overpass_ways_by_name(name, bbox):
    if bbox is None:
        return None
    s, n, w, e = bbox[0], bbox[1], bbox[2], bbox[3]
    q = f'[out:json][timeout:25];(way["name"="{name}"]({s},{w},{n},{e}););out geom;'
    key = hashlib.md5((name + str(bbox)).encode('utf8')).hexdigest()
    cachef = OSM_CACHE_DIR / f'{key}.json'
    if cachef.exists():
        try:
            return json.loads(cachef.read_text(encoding='utf8'))
        except Exception:
            pass
    try:
        r = requests.post('https://overpass-api.de/api/interpreter', data=q.encode('utf8'), headers=USER_AGENT, timeout=60)
        if r.ok:
            j = r.json()
            try:
                cachef.write_text(json.dumps(j), encoding='utf8')
            except Exception:
                pass
            time.sleep(1)
            return j
    except Exception as exc:
        print('Overpass error:', exc)
    return None

import math

def _haversine_km(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    x = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dl/2)**2)
    return 2*R*math.asin(math.sqrt(x))/1000.0


def select_best_way(overpass_result, estesa_km=None):
    ways = [e for e in overpass_result.get('elements', []) if e.get('type') == 'way']
    best = None; best_diff = float('inf')
    for w in ways:
        geom = w.get('geometry', [])
        if len(geom) < 2:
            continue
        length = 0.0
        for i in range(len(geom)-1):
            a = (geom[i]['lon'], geom[i]['lat']); b = (geom[i+1]['lon'], geom[i+1]['lat'])
            length += _haversine_km(a, b)
        w['__length_km'] = length
        diff = abs(length - estesa_km) if estesa_km else 0.0
        if diff < best_diff:
            best_diff = diff; best = w
    return best


def points_along_way(way, n_points):
    if n_points <= 0:
        return []
    coords = [(pt['lon'], pt['lat']) for pt in way.get('geometry', [])]
    if len(coords) < 2:
        return []
    seg_lengths = []
    for i in range(len(coords)-1):
        seg_lengths.append(_haversine_km(coords[i], coords[i+1]) * 1000.0)
    cum = [0.0]
    for l in seg_lengths: cum.append(cum[-1] + l)
    total = cum[-1]
    pts = []
    for k in range(n_points):
        frac = (k + 0.5) / n_points
        target = frac * total
        i = 0
        while i < len(seg_lengths) and not (cum[i] <= target <= cum[i+1]):
            i += 1
        if i >= len(seg_lengths): i = len(seg_lengths) - 1
        seg_len = seg_lengths[i] if seg_lengths[i] > 0 else 1.0
        seg_frac = (target - cum[i]) / seg_len if seg_len > 0 else 0.0
        lon1, lat1 = coords[i]; lon2, lat2 = coords[i+1]
        lon = lon1 + (lon2 - lon1) * seg_frac
        lat = lat1 + (lat2 - lat1) * seg_frac
        pts.append((lon, lat))
    return pts


def reconstruct_incidents_from_table(inc_df, province_col='PROVINCIA', road_col='NOME STRADA', estesa_col='ESTESA', incidkm_col=None):
    df = inc_df.copy()
    if incidkm_col is None:
        candidates = [c for c in df.columns if 'incid' in c.lower() or 'inc' in c.lower()]
        incidkm_col = candidates[-1] if candidates else df.columns[-1]
    results = []
    for idx, row in df.iterrows():
        name = str(row.get(road_col, '')).strip()
        prov = str(row.get(province_col, '')).strip()
        est = row.get(estesa_col, None)
        try: est_km = float(str(est).replace(',', '.')) if pd.notna(est) and str(est).strip() != '' else None
        except: est_km = None
        incidkm = row.get(incidkm_col, 0)
        try: incidkm = float(str(incidkm).replace(',', '.')) if pd.notna(incidkm) else 0.0
        except: incidkm = 0.0
        if not name:
            continue
        bbox = nominatim_bbox_for_admin('', prov) if prov else None
        if bbox is None:
            bbox = [35.0, 47.0, 6.0, 19.5]
        over = overpass_ways_by_name(name, bbox)
        if not over:
            continue
        way = select_best_way(over, est_km)
        if not way:
            continue
        length_km = way.get('__length_km', 1.0)
        n_points = int(round((incidkm or 0.0) * length_km))
        if n_points < 1:
            if (incidkm or 0) > 0:
                n_points = 1
        pts = points_along_way(way, n_points)
        for lon, lat in pts:
            results.append({'lon': lon, 'lat': lat, 'poly_name': name, 'provincia': prov, 'source_row': idx})
    if not results:
        return gpd.GeoDataFrame([], geometry=[], crs='EPSG:4326')
    return gpd.GeoDataFrame(results, geometry=gpd.points_from_xy([r['lon'] for r in results], [r['lat'] for r in results]), crs='EPSG:4326')

if __name__ == '__main__':
    N = 20
    sample = inc.head(N)
    print('Running reconstruction on', len(sample), 'rows')
    ginc = reconstruct_incidents_from_table(sample, province_col='PROVINCIA', road_col='NOME STRADA', estesa_col='ESTESA', incidkm_col='Incid/km 2017' if 'Incid/km 2017' in inc.columns else None)
    out = OSM_CACHE_DIR / 'test_reconstructed_points.geojson'
    if not ginc.empty:
        ginc.to_file(out, driver='GeoJSON')
        print('Wrote', out, 'rows=', len(ginc))
    else:
        print('No points reconstructed; check logs and cached Overpass responses in', OSM_CACHE_DIR)
