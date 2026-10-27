#!/usr/bin/env python3
"""Summarise the completed, fixed-split one-day sensor pilot without tuning."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE=Path(__file__).resolve().parents[1]


def main():
    report=json.loads((HERE/'results/sensor_sensitivity_pilot.json').read_text())
    d=pd.read_csv(HERE/'results/sensor_sensitivity_pilot.csv')
    if len(d)!=54 or d.duplicated(['repeat','training_fraction','depth','clock']).any():
        raise ValueError('Expected all 54 specified variants')
    grouped=d.groupby(['training_fraction','depth','clock']).corrected_error_pct.agg(['mean','min','max']).reset_index()
    grouped.to_csv(HERE/'results/sensor_sensitivity_summary.csv',index=False)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(9,3.5),constrained_layout=True)
    for clock,color in [('archived','#C8693F'),('local','#1F7F8C')]:
        for ax,fixed,col,title in [(axes[0],grouped.depth==3,'training_fraction','(a) Shared depth budget = 3'),
                                   (axes[1],grouped.training_fraction==1.,'depth','(b) All training-pool coils')]:
            z=grouped[fixed & (grouped.clock==clock)]
            x=z[col]*100 if col=='training_fraction' else z[col]
            ax.plot(x,z['mean'],'o-',label=f'{clock.capitalize()} input clock',color=color)
            if col=='training_fraction':
                ax.fill_between(x,z['min'],z['max'],alpha=.15,color=color)
            ax.set(title=title,ylabel='Fixed held-out count error (%)')
    axes[0].set(xlabel='Share of available training coils (%)',xticks=[25,50,100])
    axes[1].set(xlabel='Nominal shared depth budget',xticks=[1,3,5])
    for ax in axes:
        ax.axhline(report['raw_error_pct'],color='#555555',ls='--',label='Raw simulation')
        ax.set_ylim(0,max(d.corrected_error_pct.max(),report['raw_error_pct'])*1.1)
        ax.legend(fontsize=8)
    for ext in ['pdf','png']:
        fig.savefig(HERE/'figures'/f'sensor_pilot.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    table=[r'\begin{table}[htbp]\centering',
           r'\caption{Exploratory 10 February 2020 fixed-holdout pilot at shared depth budget 3. '
           r'All test targets are local time. Mean and range across three nested-training '
           r'repeats describe split sensitivity, not confidence intervals. At full training '
           r'the three sensor subsets are identical.}',
           r'\label{tab:sensor-pilot}',r'\begin{tabular}{@{}llrr@{}}\toprule',
           r'Training-pool share & Input clock & Mean error (\%) & Range \\\midrule']
    for row in grouped[grouped.depth==3].itertuples():
        table.append(f'{100*row.training_fraction:.0f}\\% & {row.clock} & {row.mean:.2f} & {row.min:.2f}--{row.max:.2f}'+r' \\')
    table.append(r'\bottomrule\end{tabular}\end{table}')
    (HERE/'tables/sensor_pilot.tex').write_text('\n'.join(table)+'\n')
    print(json.dumps(report,indent=2))
    print(grouped[grouped.depth==3].to_string(index=False))


if __name__=='__main__':
    main()
