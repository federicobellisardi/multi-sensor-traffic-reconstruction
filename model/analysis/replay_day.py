#!/usr/bin/env python3
"""Run/compare one historic day without touching the archived outputs.

Default compares existing output. --run starts the pilot only if its output does
not exist. Requires the historic workspace already prepared under article/.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, RESULTS as R1  # noqa: E402



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day',default='2020-02-10')
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    day=pd.Timestamp(args.day)
    archive=ROOT/f'work_viasat/sim{day.year}/uniq'
    old=next(archive.glob(f'*_uniq_{day:%y%m%d}_000000.csv'))
    config=old.with_name(old.name.split('_uniq_')[0]+'.json')
    out=R1/f'work/repro_{day:%Y%m%d}'
    out.mkdir(parents=True,exist_ok=True)
    outputs=list(out.glob(f'*_uniq_{day:%y%m%d}_000000.csv'))
    elapsed=None
    if args.run:
        if outputs:
            raise SystemExit('Existing replay output preserved. Compare without --run.')
        runner=ROOT/'article/python/revision/rerun/run_sims.py'
        spec=importlib.util.spec_from_file_location('historic_runner',runner)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        tag,status,elapsed=module.run(config,out,'ws')
        if status:
            raise SystemExit(f'Replay failed with status {status}; inspect {out}/{tag}.log')
        outputs=list(out.glob(f'*_uniq_{day:%y%m%d}_000000.csv'))
    if len(outputs)!=1:
        raise SystemExit('One completed replay output required; run with --run first.')
    new=outputs[0]
    a=pd.read_csv(old,sep=';').set_index(['poly_cid','oneway']).sort_index()
    b=pd.read_csv(new,sep=';').set_index(['poly_cid','oneway']).sort_index()
    cols=[c for c in a if c.startswith('20')]
    same_keys=a.index.equals(b.index)
    if not same_keys or any(c not in b for c in cols):
        raise SystemExit('Incompatible replay support; cannot compare counts.')
    delta=(a[cols]-b[cols]).abs().to_numpy()
    result={'date':args.day,'same_directed_link_keys':same_keys,
            'same_hourly_columns':list(a[cols])==list(b[cols]),
            'identical_counts':bool((delta==0).all()),
            'archive_total_link_counts':int(a[cols].sum().sum()),
            'replay_total_link_counts':int(b[cols].sum().sum()),
            'mean_absolute_cell_difference':float(delta.mean()),
            'max_absolute_cell_difference':float(delta.max()),
            'nonidentical_cell_fraction':float((delta!=0).mean()),
            'input_sha256':{},
            'interpretation':'Executable completed; historical reproducibility is determined by identical_counts. Audit binary/source/network/input compatibility before promoting reruns.'}
    prior=R1 / f'replay_{day:%Y%m%d}.json'
    if elapsed is not None:
        result['elapsed_seconds']=elapsed
    elif prior.exists():
        result['elapsed_seconds']=json.loads(prior.read_text()).get('elapsed_seconds')
    cfg=json.loads((out/f'{day:%Y%m%d}.json').read_text())
    files=[config,out/f'{day:%Y%m%d}.json',ROOT/'bin/pysim.cpython-312-x86_64-linux-gnu.so']
    files.extend(Path(cfg[k]) for k in ['file_pro','file_pnt','file_barrier','file_score_pop','file_noturn'])
    for f in files:
        result['input_sha256'][str(f.relative_to(ROOT))]=hashlib.sha256(f.read_bytes()).hexdigest()
    prior.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))


if __name__=='__main__':
    main()
