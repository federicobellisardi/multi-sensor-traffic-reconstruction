#!/usr/bin/env python3
"""Exploratory: model with relations against simulations without them, by tail, class and volume, on the existing runs. Prints a text report.

Usage: python3 od_tail_diagnostic.py OUTPUT.csv (detector-level, keep it in results/private)
"""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np,pandas as pd
from scipy.stats import spearmanr
import source_value as V, demand_scaling as D, od_matrix as M, detector_baselines as B
R=D.RUNS
arms={'model':D.OUT/'V6_scaled','noOD_fact':R/'final_experiments/fact_no_od','noOD_nofact':R/'final_experiments/nofact_no_od','N50_pairs_real':R/'od_pairing/N50_real_s1','N347':R/'od_pairing/N347_real_s1'}
rows=[]
for day in ('2020-02-10','2020-02-15'):
    for sn,t in V.sets(day).items():
        o=t.obs.values
        df=pd.DataFrame({'coil':t.coil.values,'poly':t.poly_lid.values,'obs':o,'day':day,'set':sn})
        for a,p in arms.items(): df[a]=V.daily(p,day,t.poly_lid)
        rows.append(df)
d=pd.concat(rows,ignore_index=True); d=d[(d.coil!=153)]
d.to_csv(sys.argv[1],index=False)
def met(x,o):
    m=x>0; l=np.log10(x[m]/o[m]); q=np.percentile(l,[25,75])
    return dict(sp=spearmanr(o,x)[0],sd=l.std(),iqr_sd=(q[1]-q[0])/1.349,med=np.median(np.abs(l)),f2=np.mean(np.abs(l)<np.log10(2)),low=np.mean(l<-np.log10(2)),high=np.mean(l>np.log10(2)),ratio=x.sum()/o.sum())
out=[]
for (day,sn),g in d.groupby(['day','set']):
    for a in arms: out.append({'day':day[-2:],'set':sn[:9],'arm':a,**met(g[a].values,g.obs.values)})
t=pd.DataFrame(out).round(3);print(t.to_string(index=False))
# paired model vs noOD_fact
rng=np.random.default_rng(20261103)
print('\nmodel minus noOD_fact: robust spread and Spearman, 95% bootstrap')
for (day,sn),g in d.groupby(['day','set']):
    g=g[(g.model>0)&(g.noOD_fact>0)]; lm,ln=np.log10(g.model/g.obs).values,np.log10(g.noOD_fact/g.obs).values
    def rs(x): q=np.percentile(x,[25,75]); return (q[1]-q[0])/1.349
    B_=[];n=len(g)
    for _ in range(2000):
        i=rng.integers(0,n,n);B_.append((lm[i].std()-ln[i].std(),rs(lm[i])-rs(ln[i]),np.median(np.abs(lm[i]))-np.median(np.abs(ln[i])),spearmanr(g.obs.values[i],g.model.values[i])[0]-spearmanr(g.obs.values[i],g.noOD_fact.values[i])[0]))
    ci=np.percentile(B_,[2.5,97.5],axis=0).round(3)
    print(day[-2:],sn[:9],n,'sd',ci[:,0],'robust',ci[:,1],'median',ci[:,2],'spearman',ci[:,3])
d['cls']=B.CLS.reindex(B.BAR.reindex(d.coil).values).values
print('\nmedian log10(sim/obs) by class, 2020 held out Monday')
g=d[(d.day=='2020-02-10')&(d.set=='held_out_2020')]
print(g.groupby('cls').apply(lambda x:pd.Series({'n':len(x),**{a:np.median(np.log10(x[a].clip(lower=1)/x.obs)) for a in arms}})).round(3).to_string())
print('\nby observed volume tercile, all rows: spread of log10(sim/obs)')
d['ter']=pd.qcut(d.obs,3,labels=['low','mid','high'])
print(d.groupby('ter').apply(lambda x:pd.Series({a:np.log10(x[a].clip(lower=1)/x.obs).std() for a in arms})).round(3).to_string())
print(d.groupby('ter').apply(lambda x:pd.Series({a:np.median(np.log10(x[a].clip(lower=1)/x.obs)) for a in arms})).round(3).to_string())
# where is model worse than noOD
ds=np.abs(np.log10(d.model.clip(lower=1)/d.obs))-np.abs(np.log10(d.noOD_fact.clip(lower=1)/d.obs))
print('\nshare of rows where model abs error is smaller than noOD_fact',round((ds<0).mean(),3),'median diff',round(ds.median(),3))
wrst=d.assign(ds=ds).groupby('coil').agg(ds=('ds','mean'),obs=('obs','mean'),m=('model','mean'),n=('noOD_fact','mean'),cls=('cls','first')).sort_values('ds')
print('largest gains for OD\n',wrst.head(6).round(2).to_string());print('largest losses for OD\n',wrst.tail(8).round(2).to_string())
