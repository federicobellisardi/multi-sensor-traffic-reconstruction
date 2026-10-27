# Article refresh

This directory is the working area for the revised paper. The historical source
is kept in `../paper/main.tex`; its adapted working copy is
`tex/main.tex`, preserving the original paper structure and Springer class.
The earlier `tex/text.tex` file is an exploratory analysis draft and is not the
main manuscript.

## Figure provenance

The figures included in the original paper come from three main pipelines:

| Topic in `paper/main.tex` | Original figure examples | Generating source found in the repository |
| --- | --- | --- |
| OD demand and activity | `ER-OD_heatmap_weekdays.png`, `ER-histo_weekday.png`, `ER-hourly_trend.png` | `python/od/od-1-pack.py`; further revised exploration is in `article/python/od.ipynb` |
| Coil and simulated-flow comparison | `both_plot_20220622_coil_282_compare.*.png` | `python/tools/compare_viasat_plot.py`, called by the simulation workflow |
| Viasat penetration and clusters | `histlog_penetrazione_statistica_*.png`, `major_cluster*.png`, `log_cluster_mean_*.png`, dendrograms | `python/tools/viasat_analysis.py`; a developed copy is in `article/python/viasat_analysis.py` |
| Cartographic context | `coils_distribution.png`, `cartography_ER.png` | mapping utilities in `python/preanalysis/` and `python/tools/fluxes_map.py` |

Some explanatory images in the old manuscript, including `Dijkstra.png`, do
not have a direct export command identifiable from the tracked analysis code.

## Revised figure workflow

The refreshed figure code is divided into the notebooks in `ipynb/`:

| Notebook | Content | Output directory |
| --- | --- | --- |
| `ipynb/data.ipynb` | OD demand, concentration and mobile activity | `results/figures/data/` |
| `ipynb/simulazione.ipynb` | simulated profiles, network load and correction effect | `results/figures/simulazione/` |
| `ipynb/validazione.ipynb` | Viasat distributions, ECDF/KS, penetration classes and maps | `results/figures/validazione/` |

`tex/main.tex` now reads its refreshed validation panels from
`results/figures/validazione/`. Other original panels are still available
from `../paper/` while the related sections are progressively revised.
