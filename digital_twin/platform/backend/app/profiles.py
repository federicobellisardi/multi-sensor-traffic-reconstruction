"""Run profiles: what the engine can actually be asked to do through this platform.

Perturbations are a discriminated union so future kinds (road closures) have a place, but a kind is
accepted only once the engine supports it and it has been tested.
"""
import json
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import Settings

CAMPAIGN_DAYS = ["2020-02-10", "2020-02-11", "2020-02-12", "2020-02-13", "2020-02-14", "2020-02-15", "2020-02-16", "2020-02-17",
                 "2021-06-28", "2021-06-29", "2021-06-30", "2021-07-01", "2021-07-02", "2021-07-03", "2021-07-04"]
FULL_DAY_STOP = "23:45:00"  # stop time of the frozen model
DEMO_DAY = "2000-01-03"  # deliberately outside the campaigns: demo outputs cannot be mistaken for them
CITIES = {"Piacenza": (45.0470, 9.6960), "Parma": (44.8015, 10.3279), "Reggio Emilia": (44.6989, 10.6297),
          "Modena": (44.6471, 10.9252), "Bologna": (44.4949, 11.3426), "Ferrara": (44.8381, 11.6198),
          "Ravenna": (44.4184, 12.2035), "Forli": (44.2227, 12.0407), "Rimini": (44.0678, 12.5695)}


class DemandScale(BaseModel):
    """Multiply all departures by a common factor, on top of the calibrated k of the day type."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["demand_scale"] = "demand_scale"
    factor: float = Field(1.0, gt=0, le=3)


Perturbation = Annotated[DemandScale, Field(discriminator="kind")]


class ProfileParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int | None = Field(None, ge=0, le=2_147_483_647, description="Engine seed; null keeps the engine default (1)")
    perturbations: list[Perturbation] = Field(default_factory=list, max_length=1)

    @property
    def multiplier(self) -> float:
        return self.perturbations[0].factor if self.perturbations else 1.0


class ResearchParams(ProfileParams):
    variant: Literal["V6_scaled", "V0_scaled"] = "V6_scaled"
    day: str = "2020-02-10"
    hours: int | None = Field(None, ge=1, le=23, description="Simulate the first N hours; null is the full frozen window (to 23:45)")

    @model_validator(mode="after")
    def _day(self):
        if self.day not in CAMPAIGN_DAYS:
            raise ValueError(f"day must be a campaign day: {CAMPAIGN_DAYS}")
        return self


class DemoParams(ProfileParams):
    hours: int = Field(10, ge=1, le=24, description="Simulated hours from 00:00")
    trips_per_day: int = Field(20000, ge=100, le=200000)


PROFILES = {"research_frozen": ResearchParams, "demo_synthetic": DemoParams}
DATA_CLASS = {"research_frozen": "proprietary-derived", "demo_synthetic": "synthetic"}


def validate_params(profile: str, params: dict) -> ProfileParams:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}")
    return PROFILES[profile].model_validate(params)


def is_frozen(profile: str, p: ProfileParams) -> bool:
    """True when the run is the frozen research model itself, with no platform override."""
    return profile == "research_frozen" and p.hours is None and p.seed is None and p.multiplier == 1.0


def research_missing_inputs(s: Settings) -> list[str]:
    root = s.science_root
    conf = root / "article/python/revision/rerun/work/conf_clean"
    need = [s.research_python, root / "model/analysis/demand_scaling.py", conf / "2020-02-10.json",
            s.sim_runs / "routing/V6_gps_usage_classweights/link_weights.cnt", root / "model/results/demand/k_choice.json"]
    return [str(p) for p in need if not Path(p).exists()]


def _departure_profile() -> list[float]:
    """Synthetic two-peak daily shape over 96 quarters. Not fitted to any data."""
    w = [0.15 + math.exp(-((q / 4 - 8) ** 2) / 3) + 1.1 * math.exp(-((q / 4 - 17.5) ** 2) / 5) for q in range(96)]
    t = sum(w)
    return [x / t for x in w]


def _integer_rates(trips: float, shape: list[float]) -> list[int]:
    """Departures per quarter, carrying the rounding remainder so small demand is not rounded to zero."""
    rate, carry = [], 0.0
    for x in shape:
        carry += trips * x
        n = int(carry)
        carry -= n
        rate.append(n)
    return rate


def demo_config(p: DemoParams, s: Settings, basename: str) -> dict:
    """Synthetic demand on the public project cartography: gravity-like trips between the nine provincial capitals."""
    root = s.science_root
    names = list(CITIES)
    pairs = []
    for a in names:
        for b in names:
            if a != b:
                d = math.dist(CITIES[a], CITIES[b])
                pairs.append((a, b, 1 / max(d, 0.2) ** 2))
    tot = sum(x[2] for x in pairs)
    shape = _departure_profile()
    sources = {}
    for a, b, w in pairs:
        trips = p.trips_per_day * p.multiplier * w / tot
        rate = _integer_rates(trips, shape)
        sources[f"{a}_{b}_IN"] = {
            "creation_dt": 30, "creation_rate": rate,
            "source_location": {"lat": CITIES[a][0], "lon": CITIES[a][1]},
            "dest_location": {"lat": CITIES[b][0], "lon": CITIES[b][1]},
            "pawns": {"scr_dest": {"alpha_we": 1.0, "beta_bp_miss": 0.0, "alpha_speed": 0.0, "vmin_mps": 15,
                                   "vmax_mps": 25, "cherry_pick": "medium"}},
            "spread_origin": True,
        }
    stop = f"{DEMO_DAY} {p.hours:02d}:00:00" if p.hours < 24 else f"{DEMO_DAY} 23:45:00"
    cfg = {
        "file_pro": str(root / "vars/carto/er-speed.pro"), "file_pnt": str(root / "vars/carto/er-speed.pnt"),
        "file_barrier": str(root / "vars/extra/er_barriers.csv"),
        "file_score_pop": str(root / "vars/extra/node_score_pop2021.csv"),
        "file_noturn": str(root / "vars/extra/noturn.csv"),
        "carto_cell_side": 10000, "state_grid_cell_m": 5000, "enable_geojson": False, "enable_cid_dump": False,
        "enable_gui": False, "frame_per_dt": 1, "sampling_dt": 3600, "sampling_graphics": 20, "dt": 10,
        "enable_stats": False, "enable_population": False, "state_basename": basename,
        "start_date": f"{DEMO_DAY} 00:00:00", "stop_date": stop, "sources": sources,
        "cherry_pick_mode": {"medium": 10.0}, "enable_status": True, "enable_uniq_poly": True,
        "enable_polygons": False, "dump_state_dt": -1,
    }
    if p.seed is not None:
        cfg["seed"] = p.seed
    return cfg


def research_request(p: ResearchParams, basename: str) -> dict:
    stop = None if p.hours is None else f"{p.day} {p.hours:02d}:00:00"
    return {"day": p.day, "variant": p.variant, "demand_multiplier": p.multiplier, "seed": p.seed,
            "stop_date": stop, "basename": basename}


def engine_warnings(s: Settings) -> list[str]:
    """Builds older than the seed option ignore "seed" silently and differ in the outputs."""
    engine = Path(s.sim_engine)
    if not engine.is_file():
        return []
    files = [engine, engine.parent / "libsimulation_deps.so"]
    if any(b"\0seed\0" in f.read_bytes() for f in files if f.is_file()):
        return []
    return [f"{engine} has no seed option: it is an old build and its outputs may differ from the frozen results. Rebuild with hpc/setup.sh or set SIM_ENGINE."]


def capabilities(s: Settings) -> dict:
    missing = research_missing_inputs(s)
    return {
        "engine_available": Path(s.sim_engine).is_file(),
        "engine_path": str(s.sim_engine),
        "engine_warnings": engine_warnings(s),
        "profiles": {
            "demo_synthetic": {"available": Path(s.sim_engine).is_file(), "data_class": "synthetic",
                               "schema": DemoParams.model_json_schema(),
                               "description": "SYNTHETIC demand on the real public road network. For testing the platform only; says nothing about real traffic."},
            "research_frozen": {"available": Path(s.sim_engine).is_file() and not missing, "missing_inputs": missing,
                                "data_class": "proprietary-derived", "campaign_days": CAMPAIGN_DAYS,
                                "schema": ResearchParams.model_json_schema(),
                                "description": "The frozen research configuration from model/analysis (raw simulator flows, before detector correction). Needs private inputs."},
        },
        "perturbations": {
            "demand_scale": {"supported": True, "note": "Uniform multiplier on all departures. Link volumes are not additive in demand: re-run, do not rescale outputs."},
            "road_closure": {"supported": False, "note": "Not available. The engine only has an area-based 'polygon_closed' mode, which this platform neither exposes nor has tested."},
        },
        "limits": {"max_concurrent": s.max_concurrent, "max_queued": s.max_queued, "run_timeout_s": s.run_timeout_s,
                   "run_memory_limit_gb": s.run_memory_limit_gb, "min_available_memory_gb": s.min_available_memory_gb},
    }


def resolved_config_sha(cfg_path: Path) -> str:
    """Hash of the configuration without the output location, so equal scenarios hash equally."""
    import hashlib
    c = json.load(open(cfg_path))
    c.pop("state_basename", None)
    return hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()
