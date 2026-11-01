# Regional traffic model

**A regional traffic simulation from mobile-phone, detector and GPS data: what each source adds, tested on independent observations** (target: EPJ Data Science).

| Path | Content |
|---|---|
| `analysis/` | Pipeline: demand scaling, route choice, detector correction, validation, figures and tables |
| `results/` | Aggregate results of the pipeline; link-level outputs derived from proprietary data stay in `results/private/` (git-ignored) |
| `manuscript/` | `main.tex`, `references.bib`, `supplementary/main.tex`, and the generated `figures/` and `tables/` |
| `notes/` | Reference metadata and audit of the package |

Simulations and cluster workflow: `../hpc/README.md`.

Compile, from `manuscript/`: `latexmk -pdf main.tex` and `latexmk -pdf -jobname=supplementary supplementary/main.tex`.
