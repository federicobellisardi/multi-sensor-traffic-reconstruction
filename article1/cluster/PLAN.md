# Article 1 — handoff for the IFISC cluster (nuredduna)

State on 2026-10-28, 22:15. Resume from here; the full history is in `article1/PLAN.md`.

## Rules (binding)
- No Claude/AI attribution in commits, files or the paper.
- Push only to `origin` (federicobellisardi/multi-sensor-traffic-reconstruction); never to
  `physycom` (its history contains credentials).
- Proprietary data (TIM OD, Viasat GPS, anything under `data/`, `work_viasat/`,
  `article1/results/private/`, simulation outputs) must never be committed. Only aggregate
  results, code, figures and the manuscript go to git.
- CARTO basemap key: `$MOVER/carto_key` (file, chmod 600), never in the repository.
- Target journal: EPJ Data Science. Write as a senior researcher; every number in the paper must
  come from a results file produced by the scripts.

## Layout on nuredduna
```
MOVER=/data/workspaces/fbellisardi/mover_data
$MOVER/covid_hep        git clone (must be named covid_hep)
$MOVER/sim_runs         SIM_RUNS: routing/{V6_gps_usage_classweights,V0_default_distance} (route-choice
                        files), coils/ (2021 coil table), demand/ (final simulations, created by jobs)
$MOVER/env              conda environment (created by article1/cluster/setup.sh)
$MOVER/build_minimocas  simulator build; covid_hep/minimocas/bin/sim_engine links here
$MOVER/logs             setup.log, sim_*.out/err, pipeline.out/err
$MOVER/carto_key        CARTO basemap key
```
Copied private inputs (checked by MD5): `data/old_coils_data/_coils_table_200201-000000_200331-234500.csv`,
`data/coils_{std,ave}_*.csv`, `work_viasat/viasat_*_timed_fluxes.csv`, `article1/results/private/`,
`article/python/revision/rerun/work/conf_noaug/*.json` (OD configurations without per-pair rescaling).

## Where we are
1. Correction bugs fixed (co-located coils, propagation early return, LOO overwriting outputs,
   hourly window). Committed.
2. Historic demand generator rescaled OD pairs with same-day coil counts (not independent). Now
   switched off; the whole demand is multiplied by one factor k. Scan of 10 Feb 2020 (k = 1 ... 3,
   valid inputs) -> **k = 2.0** = minimum median |log10(sim/obs)| on a calibration half of the
   coils (33 coils, seed 20261028); test half 28 coils. Volume saturates (~0.77 of observed at
   k = 2, congestion); Spearman decreases with k (0.21-0.25 at k=1 -> ~0.10 at k=2); within x2
   on test coils 11% (k=1) -> 43% (k=2); per-pair rescaling 14%. Files:
   `article1/results/demand/{k_choice.json,scan_summary.csv}`, `figures/S_demand_scan.pdf`.
3. Final simulations NOT yet run (WSL ran out of resources). They are prepared for the cluster.
4. Manuscript restructured for EPJ DS (`article1/main.tex`): Introduction (roles table,
   contributions), Data, Methods are written; Results, Discussion, Conclusions are `\tbd{}`
   placeholders. Supplement S2 (demand scale) text still quotes the INVALID morning numbers
   (k* = 1.57, "64% additivity", per-class fit) and must be rewritten with the valid scan.

## Steps
1. `tail -3 $MOVER/logs/setup.log` must end with `setup done`; otherwise
   `bash $MOVER/covid_hep/article1/cluster/setup.sh` (build + conda env).
2. `cd $MOVER/covid_hep && git pull && bash article1/cluster/submit.sh`
   - 15 simulation jobs (`demand_scaling.py one NAME DAY`: V6_scaled and V0_scaled, one per weekday
     2020-02-10..16, plus V6 2020-02-17 as determinism check), 2 cores / 6 GB / 3 h each;
   - one dependent job running `article1/cluster/pipeline.sh` (8 cores / 32 GB / 8 h).
   - The job-id parsing of `run` output is untested: if the dependency fails, wait for the 15 jobs
     (`squeue -u fbellisardi`) and submit the pipeline by hand:
     `run -t 8:00 -c 8 -m 32 env SIM_RUNS=$MOVER/sim_runs MOVER=$MOVER bash article1/cluster/pipeline.sh`
3. `pipeline.sh` does: determinism check (17 Feb simulated == 10 Feb relabelled, byte comparison;
   stops on failure) and relabelling of the other 8 days per variant; V0 assimilation/validation
   (-> `results/baseline_v0`, routing-shape table); V6 assimilation, GPS validation, distance from
   detectors, routing comparison V0 vs V6; leave-one-detector-out (stores `loo_total`); depth
   sensitivity; volume checks; `make_input_figures.py`, `make_figures.py`, `make_supp_tables.py`.
   Done when `$MOVER/logs/pipeline.out` ends with `PIPELINE_DONE`.
4. Still missing as a script: volume validation of the scaled simulation by design — 2020 excluding
   the 33 calibration coils (all campaign days), 2021 all coils; V6 vs V0 vs historic per-pair run
   (the historic run is not on the cluster: compare with the numbers in `scan_summary.csv`).
   Write it (e.g. `article1/analysis/volume_validation.py` -> `results/demand/volume_validation.json`).
5. Fill the paper:
   - Results: 4.1 demand scale (scan, k = 2.0, calibration vs test, per-pair comparison, level-rank
     trade-off); 4.2 reconstructed field (Fig 3: coil 282 withheld vs observed, hourly; daily map);
     4.3 hourly profiles (Table of baselines from `results/corrected/validation_summary.json`; Figs 4-5);
     4.4 volumes at independent detectors (step 4; routing comparison `routing_comparison.json`);
     4.5 reach of the local correction (`error_vs_detector_distance.csv`, `loo_summary.json`, Figs 6-7).
   - Discussion and Conclusions: what each sensor can validate; timing not better than simple
     profiles; volume level fixed by one parameter but ranking weak and degraded by congestion;
     local correction helps near detectors only (check with the new LOO numbers before claiming).
   - Abstract (no numbers needed, <= 350 words), fig captions, route fallback count in Methods
     (`grep "route fallbacks" $SIM_RUNS/demand/V6_scaled/*.log`), supplement S2 rewrite.
   - Remove every `\tbd{` and the `\tbd` macro; compile:
     `cd article1 && latexmk -pdf main.tex && latexmk -pdf -jobname=supplementary supplementary/main.tex`;
     check every page.
6. Senior review: each claim vs results files; statistics (bootstrap intervals where differences are
   claimed); reproducibility list in supplement S6; references used only for what their abstracts
   support; declarations (author-only items: Mindicity address, funding, contributions, ethics,
   corresponding e-mail, public repo + DOI, minimocas licence).
7. Commit code, aggregate results, figures and manuscript (no private data), push to origin.

## Useful facts
- Simulator is deterministic; demand depends only on the weekday (January 2020 OD reused for every
  day, including 2021). Config input paths must be rebuilt with `rsplit("covid_hep/", 1)`: a missing
  barrier/no-turn/population file is silently ignored by minimocas (now asserted in `v6_config`).
- About 1.2 GB RAM per simulation at k = 2; ~20-30 min per simulated day.
- Coil 282 is the example detector throughout (Fig 1d, Fig 3a).
- Route choice V6 = GPS class speeds + usage cost (alpha 0.5) + class transition weights, selected
  on Forli-Cesena GPS counts with the historic demand; not re-selected (stated in supplement S3).
