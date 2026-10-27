#!/usr/bin/env python3
"""Audit an archived MTS monthly CSV without interpreting counts as exposure.

Usage: python3 audit_mts_monthly.py INPUT.csv --output REPORT.json
Reads in chunks; does not modify raw data. Historical vehicle codes may differ
from the current official dictionary, so totals are retained separately by code.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pandas as pd


def audit(path):
    rows = 0
    missing = Counter()
    classes = Counter()
    class_rows = Counter()
    days, stations, times = set(), set(), set()
    negative = 0
    for chunk in pd.read_csv(path, chunksize=300_000):
        required = {'ANNO_ID', 'MESE_ID', 'GIO_ID', 'HHMI_ID', 'APP_ID',
                    'DIRMAR_COD', 'VEI_ID', 'NUM_TRANSITI'}
        if not required.issubset(chunk.columns):
            raise ValueError(f'Missing columns: {sorted(required - set(chunk.columns))}')
        rows += len(chunk)
        missing.update({k: int(v) for k, v in chunk.isna().sum().items()})
        days.update(int(v) for v in chunk.GIO_ID.dropna().unique())
        stations.update(int(v) for v in chunk.APP_ID.dropna().unique())
        times.update(str(v) for v in chunk.HHMI_ID.dropna().unique())
        negative += int((chunk.NUM_TRANSITI < 0).sum())
        for code, group in chunk.groupby('VEI_ID'):
            classes[int(code)] += int(group.NUM_TRANSITI.sum())
            class_rows[int(code)] += len(group)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return dict(input=str(path.resolve()), sha256=digest.hexdigest(),
                bytes=path.stat().st_size, rows=rows, days=sorted(days),
                station_count=len(stations), time_labels=sorted(times),
                missing_cells=dict(missing), negative_count_rows=negative,
                vehicle_classes={str(k): dict(rows=class_rows[k],
                                             reported_transits=classes[k])
                                 for k in sorted(classes)},
                limitations=[
                    'No cross-class sum: code 0 and historical aggregate codes require validation.',
                    'Presence of every date does not establish station-time completeness.',
                    'Timestamp time zone and DST convention remain unverified.',
                    'Current station registry is not a historical station inventory.',
                    'Station counts are not regional vehicle-kilometre exposure.'
                ])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Audited {result['rows']:,} rows; report: {args.output}")
