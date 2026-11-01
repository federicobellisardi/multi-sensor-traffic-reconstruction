#!/usr/bin/env python3
"""Exploratory fixed-holdout sensor/clock/depth experiment on 10 February 2020.

Only complete observed coils enter training/testing. The same random 20% test
coils are withheld from correction and stopping rules in every variant. Training
sets are nested within each repeat. All evaluation targets use Europe/Rome time.
The historic recursion remains unchanged; depth is its shared visited-link budget.
This one-day pilot is not full campaign validation or geographic holdout.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, RESULTS as R1  # noqa: E402

LEGACY = ROOT/'article/python/revision/loo'
WORK = R1/'work/sensor_sensitivity'
SEED = 20261027
DAY = pd.Timestamp('2020-02-10')


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    os.environ['WORKSPACE'] = str(LEGACY/'work/ws')
    spec = importlib.util.spec_from_file_location('historic_correction', LEGACY/'correction_2023.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    src = next((ROOT/'work_viasat/sim2020/uniq').glob('*_uniq_200210_000000.csv'))
    basename = src.name.split('_uniq_')[0]
    for pattern in [f'{basename}_uniq_*.csv', f'{basename}_barriers_*.csv']:
        for f in src.parent.glob(pattern):
            shutil.copy2(f, WORK/f.name)
    with contextlib.redirect_stdout(io.StringIO()):
        sim = module.SimPostCorrection({'coils_table_dir':str(LEGACY/'work/coils')},str(WORK/basename))
    obs_path = ROOT/'data/old_coils_data/_coils_table_200201-000000_200331-234500.csv'
    obs = pd.read_csv(obs_path,sep=';',index_col=0)
    obs.index = pd.to_datetime(obs.index,utc=True).tz_convert('Europe/Rome').tz_localize(None)
    obs = obs.reindex(pd.date_range(DAY,periods=96,freq='15min'))
    pivot = pd.read_csv(LEGACY/'work/ws/covid_hep/vars/extra/correction-pivot-mapping.csv',sep=';')
    mapping = {}
    for coil, dr, dc in pivot[['coil_id','dir_reg','dir_carto']].values:
        dr = 0 if dr == 0 else 1
        dc = 'IN' if dc == 'IN' else 'OUT'
        mapping[f'{coil}_{dr}']=f'{coil}_{dc}'
        mapping[f'{coil}_{1-dr}']=f'{coil}_{"OUT" if dc == "IN" else "IN"}'
    complete = []
    raw = pd.read_csv(sim.unique_file,sep=';').set_index(['poly_cid','oneway'])
    # The historic reconstruction can omit directed keys. Establish output
    # support before splitting; never silently drop a test direction mid-run.
    with contextlib.redirect_stdout(io.StringIO()):
        support_path = sim.correct(sorted(set(sim.poly2coil.values())))
    support = pd.read_csv(support_path,sep=';').set_index(['poly_cid','oneway']).index
    ambiguous = []
    incomplete_output = []
    terminal_links = []
    for coil in sorted(set(sim.poly2coil.values())):
        pcid = sim.coil2poly[coil]
        n1,n2 = sim.poly_list[pcid]
        # The historic forward-weight table does not initialise a direction
        # ending at a degree-one node unless another update later creates it.
        if any(len(sim.node_adlist[n]) < 2 for n in [n1,n2]):
            terminal_links.append(int(coil))
            continue
        if sim.polymap[n1][n2] != pcid or sim.polymap[n2][n1] != pcid:
            ambiguous.append(int(coil))
            continue
        if any((pcid,ow) not in support for ow in ['FT','TF']):
            incomplete_output.append(int(coil))
            continue
        cols = [f'{coil}_0',f'{coil}_1']
        if (all(c in obs for c in cols) and obs[cols].notna().all().all()
                and all(mapping.get(c) in sim.dfc for c in cols)
                and all((sim.coil2poly[coil], ow) in raw.index for ow in ['FT','TF'])):
            complete.append(int(coil))
    if len(complete)<10:
        raise ValueError('Insufficient complete sensors for pilot')
    observed = obs.rename(columns=mapping).resample('1h').sum(min_count=4)
    observed = observed.reindex(sim.dfc.index)[sim.dfc.columns]
    original_targets = sim.dfc.copy()
    original_map = dict(sim.poly2coil)
    cols = [c for c in raw if c.startswith('20')]
    order = np.random.default_rng(SEED).permutation(complete)
    test = sorted(order[:max(2,round(.2*len(order)))].tolist())
    train_pool = sorted(set(complete)-set(test))
    def score(table):
        absolute=0.; total=0.
        for coil in test:
            for direction,ow in [('IN','FT'),('OUT','TF')]:
                actual = observed[f'{coil}_{direction}'].to_numpy(float)
                predicted = table.loc[(sim.coil2poly[coil],ow),cols].to_numpy(float)
                if len(predicted)!=24 or not np.isfinite(actual).all():
                    raise ValueError('Incomplete test series')
                absolute += np.abs(predicted-actual).sum()
                total += actual.sum()
        return 100*absolute/total
    raw_error=score(raw)
    rows=[]
    t0=time.monotonic()
    for repeat in range(3):
        ordered=np.random.default_rng(SEED+repeat+1).permutation(train_pool)
        for fraction in [.25,.5,1.]:
            train=sorted(ordered[:max(1,round(fraction*len(ordered)))].tolist())
            sim.poly2coil={p:c for p,c in original_map.items() if c in train}
            for depth in [1,3,5]:
                sim.recursion_max_depth=depth
                for clock in ['archived','local']:
                    sim.dfc=original_targets if clock=='archived' else observed
                    with contextlib.redirect_stdout(io.StringIO()):
                        path=sim.correct(train)
                    table=pd.read_csv(path,sep=';').set_index(['poly_cid','oneway'])
                    rows.append(dict(repeat=repeat,training_fraction=fraction,training_coils=len(train),
                                     depth=depth,clock=clock,test_coils=len(test),raw_error_pct=raw_error,
                                     corrected_error_pct=score(table)))
                print(repeat,fraction,depth,round(time.monotonic()-t0,1),flush=True)
                # Save checkpoints after each pair; interruption retains completed work.
                pd.DataFrame(rows).to_csv(R1 / 'sensor_sensitivity_pilot.csv',index=False)
    report={'day':str(DAY.date()),'seed':SEED,'eligible_coils':len(complete),'test_coils':len(test),
            'excluded_ambiguous_parallel_link_coils':len(ambiguous),
            'excluded_incomplete_corrected_direction_coils':len(incomplete_output),
            'excluded_terminal_link_coils':len(terminal_links),
            'training_pool':len(train_pool),'raw_error_pct':raw_error,'variants':len(rows),
            'elapsed_seconds':time.monotonic()-t0,
            'test_set_sha256':hashlib.sha256(json.dumps(test).encode()).hexdigest(),
            'correction_source_sha256':hashlib.sha256((LEGACY/'correction_2023.py').read_bytes()).hexdigest(),
            'limitations':['One date; fixed random holdout, not geographic separation.',
                           'Only complete sensors enter training; differs from historical LOO.',
                           'All scores use local-time targets, including archived-clock variants.',
                           'Historic sibling-weight and shared-depth behaviours are retained.',
                           'Coils on ambiguous parallel graph links are excluded before splitting.',
                           'Coils lacking either direction in a structural full-correction check are excluded before splitting.',
                           'Terminal-link coils are excluded because the historic code can drop their held-out direction.',
                           'Repeated 100% training subsets are identical and not independent replicates.',
                           'No GPS data or test errors were used to select training sensors.']}
    (WORK/'split.json').write_text(json.dumps({'test':test,'train_pool':train_pool},indent=2)+'\n')
    (R1 / 'sensor_sensitivity_pilot.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
