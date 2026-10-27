# Article 1 — traffic reconstruction

Working manuscript: **Large-scale traffic flow reconstruction from heterogeneous
mobility sensors**. Status: internal research draft; **not submission-ready**.
See `reports/` for the implementation audit and evidence tables.

## Contents

| Path | Purpose |
|---|---|
| `main.tex`, `main.pdf` | New reconstruction-only manuscript in the inherited Springer style |
| `supplementary/main.tex`, `supplementary.pdf` | Supporting data/method tables, selected-road examples and limitations |
| `analysis/` | Archive validation, reference verification, one-day replay and sensor pilot |
| `figures/`, `tables/` | Inherited assets and regenerated validation/diagnostics |
| `results/` | Aggregate JSON/CSV outputs and input/environment provenance |
| `results/private/` | Ignored local link-level outputs derived from proprietary GPS |
| `reports/` | Literature, publication strategy, claim audit and implementation findings |

Original material remains in `../article/` and `../paper/`. Large/proprietary
inputs are referenced in place rather than copied into this package. This
workspace currently depends on the parent repository; it is not standalone.

## Reproduce

From the **parent repository root**:

```sh
python3 article1/analysis/validate_archive.py
python3 article1/analysis/verify_references.py
python3 article1/analysis/replay_day.py
# Optional one-day random-holdout experiment; several minutes:
python3 article1/analysis/sensor_sensitivity.py
python3 article1/analysis/summarize_sensor_pilot.py
python3 article1/analysis/plot_time_shift.py
```

Validation requires local GPS extracts and raw/assimilated simulation archives
under `work_viasat/`, public MTS inputs under `data/`, and the historic LOO table
under `article/results/revision/`. The sensor pilot additionally requires the
historic metadata/coils workspace in `article/python/revision/loo/work/`.
The reference verifier uses cached Crossref records when available. It does not
invent a citation if the API fails.

`replay_day.py` defaults to comparing existing local replay outputs. On a clean
machine, `--run` invokes the Python 3.12 `pysim` binary through the inherited
runner; the historic workspace is required. It preserves existing replay
outputs. The completed one-day replay differs numerically from the archive,
so a successful process exit must not be interpreted as historical reproduction.

Compile from **inside `article1/`**, main first for cross-document references:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
latexmk -pdf -jobname=supplementary -interaction=nonstopmode -halt-on-error supplementary/main.tex
# Then, from the parent repository root:
# python3 article1/analysis/package_audit.py
```

Python dependencies for the new analysis are NumPy, pandas and Matplotlib;
versions are recorded in `results/validation_summary.json`. The source class
`sn-jnl.cls` is copied from the reference manuscript. TeX Live/pdfLaTeX, BibTeX
and latexmk are needed for PDFs. Poppler utilities and Pillow were used only
for local visual inspection, not for generating the statistical results.

## Reading the evidence

GPS errors test hourly **shape**, not total volume. The MTS profile outperforms
the archived reconstruction. The legacy counter result uses UTC as local and
omits 18 directional coil-day records; its bootstrap inherits these defects.
The sensor pilot has a smaller, restricted sample and is exploratory. Read
`reports/IMPLEMENTATION_AUDIT.md` before interpreting either experiment.

Figures 1–4 and the selected-road supplementary panels are inherited and have
not all been regenerated. The new `validation.pdf` and `diagnostics.pdf` figures
are produced from local data by the new analysis. The bibliography's selected
DOI entries have verified Crossref metadata, including a corrected Mobile
Century DOI. Affiliation details, ethics/access arrangements and author
declarations remain explicitly marked for confirmation.

No original analyses were overwritten, no commits were made, and no data or
manuscript were published or uploaded.
