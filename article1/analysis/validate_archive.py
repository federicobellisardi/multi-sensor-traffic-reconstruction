#!/usr/bin/env python3
"""Recompute Article 1 validation from local archives; never writes to article/.

Run from any directory: python3 article1/analysis/validate_archive.py
Private link-level tables go to ignored results/private/. Public outputs contain
aggregate statistics, figure data and tables only. No fitted time shift is applied.
"""
import hashlib
import json
import platform
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
OUT = HERE / 'results'
H = pd.Index(range(24), name='hour')
CAMPAIGNS = {
    2020: 'viasat_20200210_20200218_timed_fluxes.csv',
    2021: 'viasat_20210628_20210705_timed_fluxes.csv',
}


def quantiles(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {'n': 0}
    return dict(n=len(a), **{k: float(np.percentile(a, q)) for k, q in
                            [('p10', 10), ('p25', 25), ('median', 50),
                             ('p75', 75), ('p90', 90)]})


def load_sim(path):
    d = pd.read_csv(path, sep=';')
    cols = [c for c in d if c.startswith('20')]
    if len(cols) != 24 or len(set(pd.to_datetime(cols).hour)) != 24:
        raise ValueError(f'Expected all 24 start-labelled hours: {path}')
    if d.duplicated(['poly_cid', 'oneway']).any():
        raise ValueError(f'Duplicate directed link keys: {path}')
    s = d.groupby('poly_cid')[cols].sum().T
    s.index = pd.to_datetime(s.index).hour
    if (s < 0).any().any() or s.isna().any().any():
        raise ValueError(f'Invalid counts: {path}')
    return s.reindex(H).astype(float)


def demand(path):
    c = json.loads(path.read_text())
    rates = [np.asarray(s['creation_rate'][:96], float) for s in c['sources'].values()]
    if any(len(r) != 96 for r in rates):
        raise ValueError(f'Non-daily creation-rate vector: {path}')
    return np.sum(rates, axis=0).reshape(24, 4).sum(axis=1)


def counter_profiles(days, year):
    if year == 2020:
        p = ROOT / 'data/old_coils_data/_coils_table_200201-000000_200331-234500.csv'
        d = pd.read_csv(p, sep=';', index_col=0)
        d.index = pd.to_datetime(d.index, utc=True).tz_convert('Europe/Rome').tz_localize(None)
        d = d[np.isin(d.index.date, days)]
        expected = pd.DatetimeIndex([pd.Timestamp(day) + pd.Timedelta(minutes=15*k)
                                     for day in days for k in range(96)])
        if d.index.duplicated().any():
            raise ValueError('Duplicate MTS timestamps')
        d = d.reindex(expected)
        d = d.loc[:, d.notna().all()]
        d = d.loc[:, d.sum() > 0]
        daily = {day: d[d.index.date == day].groupby(lambda x: x.hour).sum().reindex(H)
                 for day in days}
    else:
        p = ROOT / 'data/coils_ave_220101-000000_221231-234500.csv'
        a = pd.read_csv(p, sep=';')
        a = a[a.season == 'summer']
        cols = [c for c in a if c.endswith(('_0', '_1'))]
        daily = {}
        for day in days:
            z = a[a.wday_n == int(pd.Timestamp(day).strftime('%w'))].copy()
            z['hour'] = pd.to_datetime(str(day) + ' ' + z.time).dt.hour
            z = z.groupby('hour')[cols].sum(min_count=1).reindex(H)
            daily[day] = z.loc[:, z.notna().all() & (z.sum() > 0)]
    return daily


def metrics(s, g, od, mts):
    common = s.columns.intersection(g.columns)
    common = common[(s[common].sum() > 0) & (g[common].sum() > 0)]
    ps, pg = s[common] / s[common].sum(), g[common] / g[common].sum()
    mae = lambda pred: 100 * pg.sub(pred, axis=0).abs().mean()
    m = pd.DataFrame({'mae_pp': 100 * (ps-pg).abs().mean(),
                      'pearson': ps.corrwith(pg), 'gps_total': g[common].sum(),
                      'sim_total': s[common].sum()})
    m.index.name = 'cid'
    m['eta'] = m.gps_total / m.sim_total
    m['mae_pp_od'] = mae(od / od.sum())
    m['mae_pp_mts'] = mae(mts)
    m['mae_pp_flat'] = mae(np.ones(24)/24)
    return m, ps, pg


def summarize(m):
    return {'links': len(m), **{c: quantiles(m[c]) for c in
                              ['mae_pp', 'pearson', 'mae_pp_od', 'mae_pp_mts', 'mae_pp_flat']},
            'share_better_od': float((m.mae_pp < m.mae_pp_od).mean()),
            'share_better_mts': float((m.mae_pp < m.mae_pp_mts).mean()),
            'median_paired_gain_od_pp': float((m.mae_pp_od - m.mae_pp).median()),
            'median_paired_gain_mts_pp': float((m.mae_pp_mts - m.mae_pp).median())}


def main():
    (OUT/'private').mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42})
    summary = {'protocol': {
        'same_date_matching': True, 'gps_directions': 'summed before comparison',
        'normalization': 'each link divided by its own campaign/day-type total',
        'shift': 'none', 'missing_gps_policy': 'explicit zero-filled absent link-hour records',
        'limitations': ['GPS zero versus absent observation is not identifiable from extract.',
                        '2021 MTS comparator is a 2022 seasonal profile; not same-year ground truth.',
                        'Links are spatially dependent; no independent-link confidence interval.',
                        'Weekends contain two days per campaign; descriptive estimates only.']},
        'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                        'pandas': pd.__version__, 'matplotlib': matplotlib.__version__}}
    figures, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    daytype_rows = []
    for j, (year, gps_name) in enumerate(CAMPAIGNS.items()):
        gps_path = ROOT/'work_viasat'/gps_name
        v = pd.read_csv(gps_path, sep=';', parse_dates=['time'])
        if (v.total_fluxes < 0).any() or v.total_fluxes.isna().any():
            raise ValueError('Invalid GPS counts')
        days = sorted(v.time.dt.date.unique())
        daily_g = {day: v[v.time.dt.date == day].groupby([v.time.dt.hour, 'cid'])
                   .total_fluxes.sum().unstack(fill_value=0).reindex(H, fill_value=0)
                   for day in days}
        folder = ROOT/f'work_viasat/sim{year}/uniq'
        sim, raw, od = {}, {}, {}
        input_files = [gps_path]
        for day in days:
            files = list(folder.glob(f'*_uniq_{pd.Timestamp(day):%y%m%d}_000000.csv'))
            if len(files) != 1:
                raise ValueError(f'Expected one raw archive for {day}, got {files}')
            f = files[0]
            corrected = Path(str(f)+'.corrected')
            cfg = f.with_name(f.name.split('_uniq_')[0]+'.json')
            sim[day], raw[day], od[day] = load_sim(corrected), load_sim(f), demand(cfg)
            input_files.extend([f, corrected, cfg])
        cp = counter_profiles(days, year)
        campaign = {'days': [str(d) for d in days], 'day_types': {},
                    'counter_directions': {str(d): len(cp[d].columns) for d in days}}
        all_m = None
        for kind in ['all', 'weekday', 'weekend']:
            selected = [d for d in days if kind == 'all' or
                        (pd.Timestamp(d).dayofweek < 5) == (kind == 'weekday')]
            s = sum(sim[d] for d in selected)
            g = sum((daily_g[d] for d in selected))
            o = sum(od[d] for d in selected)
            # Match the legacy 2020 comparator: normalise each direction after
            # pooling dates. For 2021: average daily seasonal direction profiles.
            if year == 2020:
                c = sum(cp[d] for d in selected)
                mts = (c/c.sum()).mean(axis=1).values
            else:
                mts = np.mean([(cp[d]/cp[d].sum()).mean(axis=1).values for d in selected], axis=0)
            m, ps, pg = metrics(s, g, o, mts)
            mr, _, _ = metrics(sum(raw[d] for d in selected), g, o, mts)
            m['mae_pp_raw'] = mr.mae_pp.reindex(m.index)
            m.to_csv(OUT/'private'/f'link_metrics_{year}_{kind}.csv')
            stats = summarize(m)
            stats.update(days=len(selected), mae_pp_raw=quantiles(m.mae_pp_raw))
            campaign['day_types'][kind] = stats
            daytype_rows.append({'year': year, 'day_type': kind, 'days': len(selected),
                                 'links': len(m), **{key: stats[key]['median'] for key in
                                                  ['mae_pp','mae_pp_raw','mae_pp_od','mae_pp_mts','pearson']}})
            if kind == 'all':
                all_m = m
                # The legacy script reports mean daily simulated counts; our
                # campaign sum is equivalent after normalisation and eta scaling.
                prior = pd.read_csv(ROOT/f'article/results/revision/link_metrics_{year}.csv').set_index('cid')
                cols = ['mae_pp','mae_pp_raw','mae_pp_od','mae_pp_mts','pearson','eta']
                campaign['legacy_max_absolute_difference'] = {
                    c: float((m[c]-prior[c].reindex(m.index)).abs().max()) for c in cols}
                check_cols = [c for c in cols if not (year == 2021 and c == 'mae_pp_mts')]
                if year == 2021:
                    campaign['mts_missingness_change'] = {
                        'old': 'groupby.sum converts all-missing hourly cells into zero',
                        'new': 'sum(min_count=1); exclude incomplete direction profiles',
                        'legacy_median_mae_pp': float(prior.mae_pp_mts.median()),
                        'strict_median_mae_pp': float(m.mae_pp_mts.median())}
                if set(m.index) != set(prior.index) or any(
                        campaign['legacy_max_absolute_difference'][c] > 1e-9 for c in check_cols):
                    raise ValueError(f'Archive reproduction mismatch: {year}')
                ax = axes[0, j]
                for col, lab, color, ls in [('mae_pp', 'Assimilated', '#1F7F8C','-'),
                                          ('mae_pp_raw','Raw simulation','#C8693F','-'),
                                          ('mae_pp_od','OD profile','#777777',':'),
                                          ('mae_pp_mts','MTS profile','#333333','--')]:
                    vals = np.sort(m[col])
                    ax.step(vals, np.arange(1,len(vals)+1)/len(vals), where='post',
                            label=lab, color=color, ls=ls)
                ax.set(xlabel='Hourly-share MAE (percentage points)', ylabel='Fraction of links',
                       xlim=(0,6), title=f'({chr(97+j)}) {year}, {len(m)} links')
                ax.legend(fontsize=8)
                # Aggregate shares weight links by simulated/GPS counts separately.
                agg_s, agg_g = s[m.index].sum(axis=1), g[m.index].sum(axis=1)
                a = pd.DataFrame({'hour': range(24), 'sim_share': agg_s/agg_s.sum(),
                                  'gps_share': agg_g/agg_g.sum(), 'mts_share': mts,
                                  'od_share': o/o.sum()})
                a.to_csv(OUT/f'aggregate_profiles_{year}.csv',index=False)
                campaign['aggregate_peak_hour_sim'] = int(agg_s.idxmax())
                campaign['aggregate_peak_hour_gps'] = int(agg_g.idxmax())
                campaign['probe_count_strata'] = {
                    name: summarize(m[mask]) for name, mask in
                    [('1-49', m.gps_total < 50), ('50-199',m.gps_total.between(50,199)),
                     ('200+',m.gps_total>=200)] if mask.any()}
        ax = axes[1,j]
        for kind, color in [('weekday','#1F7F8C'),('weekend','#C8693F')]:
            vals = np.sort(pd.read_csv(OUT/'private'/f'link_metrics_{year}_{kind}.csv').mae_pp)
            ax.step(vals,np.arange(1,len(vals)+1)/len(vals),where='post',color=color,
                    label=f'{kind.capitalize()} ({campaign["day_types"][kind]["days"]} days)')
        ax.set(xlabel='Hourly-share MAE (percentage points)',ylabel='Fraction of links',
               xlim=(0,6),title=f'({chr(99+j)}) {year}, day-type sensitivity')
        ax.legend(fontsize=8)
        campaign['input_sha256'] = {}
        for f in input_files:
            campaign['input_sha256'][str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
        summary[str(year)] = campaign
        print(year, json.dumps(campaign['day_types']['all']), flush=True)
    for ext in ['pdf','png']:
        figures.savefig(HERE/'figures'/f'validation.{ext}',dpi=300,bbox_inches='tight')
    plt.close(figures)
    pd.DataFrame(daytype_rows).to_csv(OUT/'daytype_summary.csv',index=False)
    (OUT/'validation_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    loo_audit()
    make_tables_and_diagnostics(summary, daytype_rows)


def loo_audit():
    """Sensor-cluster bootstrap of existing LOO predictions, not a new LOO run."""
    d = pd.read_csv(ROOT/'article/results/revision/loo_coils_2020.csv')
    by = d.groupby('coil')[['obs_total','raw_abs','loo_abs']].sum()
    a = by.to_numpy()
    rng = np.random.default_rng(20261027)
    vals = []
    for _ in range(5000):
        sample = a[rng.integers(0,len(a),len(a))].sum(axis=0)
        vals.append(100*(sample[1]-sample[2])/sample[0])
    gain = 100*(a[:,1].sum()-a[:,2].sum())/a[:,0].sum()
    report = {'source': 'article/results/revision/loo_coils_2020.csv',
              'coils': len(by), 'coil_days': d.groupby(['coil','day']).ngroups,
              'directional_records': len(d),
              'missing_directions_relative_to_two_per_coil_day': int(2*d.groupby(['coil','day']).ngroups-len(d)),
              'pooled_raw_error_pct': 100*a[:,1].sum()/a[:,0].sum(),
              'pooled_loo_error_pct': 100*a[:,2].sum()/a[:,0].sum(),
              'pooled_error_reduction_pp': gain,
              'sensor_cluster_bootstrap_95pct_pp': np.percentile(vals,[2.5,97.5]).tolist(),
              'replicates': 5000, 'seed': 20261027,
              'interpretation': 'Conditional sensor-resampling interval. Spatial dependence between sensors, clock defects and model uncertainty are not captured.',
              'leave_one_day_out_error_reduction_pp': {}}
    for day in sorted(d.day.unique()):
        z = d[d.day != day]
        report['leave_one_day_out_error_reduction_pp'][day] = float(
            100*(z.raw_abs.sum()-z.loo_abs.sum())/z.obs_total.sum())
    (OUT/'loo_uncertainty.json').write_text(json.dumps(report,indent=2)+'\n')


def make_tables_and_diagnostics(summary, rows):
    probe = [r'\begin{table}[htbp]\centering',
             r'\caption{Profile error by total campaign probe count, independent of the '
             r'simulated-volume denominator. Groups are descriptive; probe trajectories and '
             r'neighbouring links are dependent.}',
             r'\begin{tabular}{@{}llrrrr@{}}\toprule',
             r'Campaign & Probes & Links & Assimilated MAE & MTS MAE & Correlation \\\midrule']
    for year in CAMPAIGNS:
        for group, d in summary[str(year)]['probe_count_strata'].items():
            probe.append(f'{year} & {group} & {d["links"]} & '
                         f'{d["mae_pp"]["median"]:.2f} & {d["mae_pp_mts"]["median"]:.2f} & '
                         f'{d["pearson"]["median"]:.2f}'+r' \\')
    probe.append(r'\bottomrule\end{tabular}\end{table}')
    (HERE/'tables/probe_strata.tex').write_text('\n'.join(probe)+'\n')
    table = [r'\begin{table}[htbp]\centering',
             r'\caption{Median hourly-share MAE (pp) on all usable links in each campaign and day type. '
             r'Link sets depend on non-zero totals within the selected days. MTS in 2021 is a '
             r'2022 seasonal comparator, excluding direction profiles with missing hours.}',
             r'\label{tab:baselines}', r'\begin{tabular}{@{}llrrrrrr@{}}\toprule',
             r'Campaign & Days & Links & Raw & Assimilated & OD & MTS & Uniform \\\midrule']
    for year in CAMPAIGNS:
        for kind in ['all','weekday','weekend']:
            d = summary[str(year)]['day_types'][kind]
            nums = [d[k]['median'] for k in ['mae_pp_raw','mae_pp','mae_pp_od','mae_pp_mts','mae_pp_flat']]
            table.append(f'{year} & {kind} ({d["days"]}) & {d["links"]} & '+
                         ' & '.join(f'{x:.2f}' for x in nums)+r' \\')
        if year == 2020:
            table.append(r'\midrule')
    table.extend([r'\bottomrule\end{tabular}\end{table}'])
    (HERE/'tables/baselines.tex').write_text('\n'.join(table)+'\n')
    fig = plt.figure(figsize=(10,6), constrained_layout=True)
    grid = fig.add_gridspec(2,2)
    for j, year in enumerate(CAMPAIGNS):
        ax = fig.add_subplot(grid[j,0])
        d = pd.read_csv(OUT/f'aggregate_profiles_{year}.csv')
        for col, label, color, ls in [('sim_share','Assimilated','#1F7F8C','-'),
                                     ('gps_share','GPS probes','#C8693F','-'),
                                     ('mts_share','MTS profile','#555555','--')]:
            ax.plot(d.hour,100*d[col],color=color,ls=ls,label=label)
        ax.set(xlabel='Hour (interval start)',ylabel='Hourly share (%)',
               xticks=range(0,24,3),title=f'({chr(97+j)}) {year}, pooled link counts')
        ax.legend(fontsize=8,ncol=3)
    ax = fig.add_subplot(grid[:,1])
    d = pd.read_csv(ROOT/'article/results/revision/loo_coils_2020.csv')
    by = d.groupby('coil')[['obs_total','raw_abs','loo_abs']].sum()
    changed = d.groupby('coil').changed.any()
    x,y = 100*by.raw_abs/by.obs_total, 100*by.loo_abs/by.obs_total
    for mask,label,color in [(changed,'Reached by propagation','#C8693F'),
                             (~changed,'Not reached','#999999')]:
        ax.scatter(x[mask],y[mask],s=20,color=color,label=label,alpha=.8)
    hi = max(x.max(),y.max())*1.05
    ax.plot([0,hi],[0,hi],'k--',lw=1)
    ax.set(xlabel='Held-out error, raw simulation (%)',
           ylabel='Held-out error, other coils assimilated (%)',
           xlim=(0,hi),ylim=(0,hi),title='(c) 2020 leave-one-counter-out')
    ax.set_aspect('equal',adjustable='box')
    ax.legend(fontsize=8)
    for ext in ['pdf','png']:
        fig.savefig(HERE/'figures'/f'diagnostics.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
