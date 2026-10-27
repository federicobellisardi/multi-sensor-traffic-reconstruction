#!/usr/bin/env python3
"""Hour-label convention of the TIM OD tables.

Compares the hourly share of all OD activity (raw hourly tables data/tables_rpc-rpc/<yymmddHH00>.csv,
weekdays 10-14 Feb 2020) with the local-time, start-labelled hourly share of the MTS coils complete
on the same days. The best agreement at lag 0 (OD label h = local interval [h, h+1)) supports the
fixed_clock mapping used in run_corrected_sims.py.
"""
import numpy as np, pandas as pd, glob, os
from pathlib import Path
R=str(Path(__file__).resolve().parents[2])+'/'
days=['200210','200211','200212','200213','200214']
od=np.zeros(24)
for d in days:
    for h in range(24):
        f=f'{R}data/tables_rpc-rpc/{d}{h:02d}00.csv'
        x=pd.read_csv(f,sep=';',skiprows=3,header=None,low_memory=False)
        od[h]+=pd.to_numeric(x.iloc[:,4:].stack(),errors='coerce').sum()
od/=od.sum()
c=pd.read_csv(R+'data/old_coils_data/_coils_table_200201-000000_200331-234500.csv',sep=';',index_col=0)
c.index=pd.to_datetime(c.index,utc=True).tz_convert('Europe/Rome').tz_localize(None)
c=c[np.isin(c.index.strftime('%y%m%d'),days)]
c=c.loc[:,c.notna().all()]
cp=c.groupby(c.index.hour).sum().sum(axis=1).values; cp=cp/cp.sum()
print('ncoils',c.shape[1])
print('h  OD_label  coils_local(start-labelled)')
for h in range(24): print(f'{h:2d} {100*od[h]:6.2f} {100*cp[h]:6.2f}')
for lag in [-1,0,1]:
    print('lag',lag,'MAE pp',np.mean(np.abs(np.roll(od,lag)-cp))*100,'corr',np.corrcoef(np.roll(od,lag),cp)[0,1])
