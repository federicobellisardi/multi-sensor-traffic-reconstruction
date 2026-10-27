"""Leave-one-out test of the coil-based assimilation (archived 2023-03-30 algorithm).

For every coil with complete 15-min data on the simulated day, the coil is removed both
from the assimilation input and from the set of polylines that stop the propagation; the
assimilation is rerun and the hourly counts on the held-out polyline are compared with
the observed coil counts before (raw simulation) and after assimilation.
"""
import sys, os, glob, json
import numpy as np, pandas as pd
import warnings; warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['WORKSPACE'] = os.path.join(HERE, 'ws')
from correction_2023 import SimPostCorrection
import io, contextlib

basename = sys.argv[1]; out = sys.argv[2]
cfg = {'coils_table_dir': os.path.join(HERE, 'coils')}
with contextlib.redirect_stdout(io.StringIO()):
    sim = SimPostCorrection(cfg, basename)
raw = pd.read_csv(sim.unique_file, sep=';')
cols = [c for c in raw.columns if c.startswith('20')]
day = pd.to_datetime(cols[0]).normalize()

# observed 15-min table, complete days only (both directions, 96 samples)
obs = pd.read_csv(os.path.join(HERE, 'coils', 'coils_table_200201-000000_200331-234500.csv'), sep=';', index_col=0)
obs.index = pd.to_datetime(obs.index).tz_localize(None)
obs = obs[(obs.index >= day) & (obs.index < day + pd.Timedelta(days=1))]
coils_mapped = set(int(v) for v in sim.poly2coil.values())
complete = []
for c in sorted(coils_mapped):
    cc = [f'{c}_0', f'{c}_1']
    if all(x in obs.columns for x in cc) and len(obs) == 96 and obs[cc].notna().all().all():
        complete.append(c)

# observed hourly counts in the cartographic IN/OUT convention used by the assimilation
dfc = sim.dfc  # hourly, columns like '282_IN'
def poly_rows(table, pcid):
    t = table[table.poly_cid == pcid].set_index('oneway')
    return t
base_poly2coil = dict(sim.poly2coil)
all_tags = list(sim.dfb.tag.values)

def run(excluded):
    sim.poly2coil = {k: v for k, v in base_poly2coil.items() if v != excluded}
    sel = [t for t in all_tags if t != excluded]
    with contextlib.redirect_stdout(io.StringIO()):
        f = sim.correct(sel)
    return pd.read_csv(f, sep=';')

full = run(None)
rows = []
for c in complete:
    pcid = sim.coil2poly[c]
    loo = run(c)
    for d_carto, ow in [('IN', 'FT'), ('OUT', 'TF')]:
        key = f'{c}_{d_carto}'
        if key not in dfc.columns: continue
        o = dfc[key].values.astype(float)
        r = raw[(raw.poly_cid == pcid) & (raw.oneway == ow)][cols].values.ravel().astype(float)
        a = loo[(loo.poly_cid == pcid) & (loo.oneway == ow)][cols].values.ravel().astype(float)
        fl = full[(full.poly_cid == pcid) & (full.oneway == ow)][cols].values.ravel().astype(float)
        if len(r) != 24 or len(a) != 24: continue
        rows.append(dict(day=str(day.date()), coil=c, poly_cid=pcid, direction=d_carto,
                         obs_total=o.sum(), raw_abs=np.abs(r - o).sum(), loo_abs=np.abs(a - o).sum(),
                         full_abs=np.abs(fl - o).sum(), changed=bool(np.any(np.abs(a - r) > 0.5))))
    print(c, flush=True)
pd.DataFrame(rows).to_csv(out, index=False)
