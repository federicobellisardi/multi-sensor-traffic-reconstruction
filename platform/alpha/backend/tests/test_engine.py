"""Against the real sim_engine. Skipped when it is not built; requires ALPHA_TEST_ENGINE or SIM_ENGINE."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_ROOT, Settings
from app.main import create_app
from conftest import wait

ENGINE = Path(os.environ.get("SIM_ENGINE", "/nonexistent"))
pytestmark = pytest.mark.skipif(not ENGINE.is_file(), reason="sim_engine not built")


@pytest.fixture
def real(tmp_path):
    s = Settings(state_dir=tmp_path / "state", science_root=REPO_ROOT, sim_engine=ENGINE, sim_runs=tmp_path / "none", research_python=tmp_path / "none",
                 frontend_dist=tmp_path / "none", poll_s=0.2, run_memory_limit_gb=6)
    with TestClient(create_app(s)) as c:
        yield c


def test_engine_has_seed_option(real):
    assert real.get("/api/capabilities").json()["engine_warnings"] == []


def run(c, name, **params):
    sc = c.post("/api/scenarios", json={"name": name, "profile": "demo_synthetic", "params": {"hours": 2, "trips_per_day": 40000, **params}}).json()
    return wait(c, c.post(f"/api/scenarios/{sc['id']}/runs").json()["id"], ["completed", "failed"], timeout=600)


def test_seed_determinism_and_flow_conservation(real):
    a, b = run(real, "a", seed=11), run(real, "b", seed=11)
    d = run(real, "c", seed=12)
    assert a["status"] == b["status"] == d["status"] == "completed", a["error"]
    f = real.get(f"/api/runs/{a['id']}/flows").json()
    assert len(f["flow"]) == 3925 and sum(f["flow"]) > 0 and min(f["flow"]) >= 0, "the demo must actually move vehicles"
    assert a["output_sha256"] == b["output_sha256"], "same configuration and seed must reproduce the output byte by byte"
    assert a["config_sha256"] == b["config_sha256"]
    assert d["output_sha256"] != a["output_sha256"], "the seed must change the stochastic realisation"


def test_engine_failure_is_reported(real, tmp_path):
    # the config generator is fine; an unreadable network file makes the real engine fail
    settings = real.app.state.jobs.s
    settings.science_root = tmp_path
    (tmp_path / "x").write_text("")
    sc = real.post("/api/scenarios", json={"name": "bad", "profile": "demo_synthetic", "params": {"hours": 1}}).json()
    r = wait(real, real.post(f"/api/scenarios/{sc['id']}/runs").json()["id"], ["completed", "failed"], timeout=120)
    assert r["status"] == "failed" and r["error"]
