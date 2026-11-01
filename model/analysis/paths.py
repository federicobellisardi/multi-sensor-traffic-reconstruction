"""Locations used by the Article 1 analysis scripts (all relative to the repository, overridable by environment).

ROOT     repository root
ARTICLE  manuscript directory (figures/ and tables/ included in the paper)
RESULTS  aggregate results of the analysis; RESULTS/private holds link-level outputs derived from
         proprietary data (git-ignored)
SIM_RUNS simulation outputs and route-choice inputs (large, not in the repository)
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "model" / "manuscript"
RESULTS = Path(os.environ.get("RESULTS_DIR", ROOT / "model/results"))
SIM_RUNS = Path(os.environ.get("SIM_RUNS", ROOT / "sim_runs"))
DATA_CACHE = Path(os.environ.get("DATA_CACHE", ROOT / "data/cache"))  # downloaded public data (MTS monthly tables, OSM extract)
SIM_ENGINE = Path(os.environ.get("SIM_ENGINE", ROOT / "minimocas/bin/sim_engine"))  # minimocas executable (see hpc/setup.sh)
