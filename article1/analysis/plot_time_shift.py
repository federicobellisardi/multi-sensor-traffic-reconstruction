#!/usr/bin/env python3
"""Display an explicitly declared +1 h shift; no data correction or fitted metric."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parents[1]


def main():
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    for ax, year in zip(axes, [2020, 2021]):
        d = pd.read_csv(HERE / f'results/aggregate_profiles_{year}.csv')
        ax.plot(d.hour, 100*d.gps_share, color='#C8693F', label='GPS probes')
        ax.plot(d.hour, 100*d.sim_share, color='#999999', ls=':', label='Simulation, original')
        ax.plot(d.hour+1, 100*d.sim_share, color='#1F7F8C', label='Simulation, displayed +1 h')
        ax.set(title=str(year), xlabel='Hour (interval start)', ylabel='Hourly share (%)',
               xlim=(0, 24), xticks=list(range(0, 25, 3)), ylim=(0, None))
        ax.legend(fontsize=8)
    for ext in ['pdf', 'png']:
        fig.savefig(HERE / f'figures/time_shift_sensitivity.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main()
