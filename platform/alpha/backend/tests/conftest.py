import os
import stat
import sys
import textwrap
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import REPO_ROOT, Settings  # noqa: E402
from app.main import create_app  # noqa: E402

FAKE = """#!{py}
# Stand-in for sim_engine, only for runner tests. Behaviour chosen by the config's stop hours.
import json, sys, time
c = json.load(open(sys.argv[1])); b = c["state_basename"]; h = int(c["stop_date"][11:13]) or 24
print("fake engine", flush=True)
if h == 1:
    print("boom: invalid network", flush=True); sys.exit(0)  # the real engine exits 0 on exceptions
if h == 2:
    sys.exit(3)
n = 100
for i in range(n + 1):
    open(b + ".status", "a").write(f"{{i}};{{n}};2026-01-01 00:00:00\\n")
    time.sleep(0.2 if h == 3 else 0.001)
head = ";".join(f"2000-01-03 {{x:02d}}:00:00" for x in range(h))
with open(b + "_uniq_000103_000000.csv", "w") as f:
    f.write("poly_lid;poly_cid;oneway;" + head + "\\n")
    for lid, cid in enumerate([0, 23]):
        for d, w in (("FT", 1), ("TF", 2)):
            f.write(f"{{lid}};{{cid}};{{d}};" + ";".join(str(w * (x + 1)) for x in range(h)) + "\\n")
"""


def wait(client, run_id, states, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = client.get(f"/api/runs/{run_id}").json()
        if r["status"] in states:
            return r
        time.sleep(0.05)
    raise AssertionError(f"timeout, last state {r}")


@pytest.fixture
def settings(tmp_path):
    fake = tmp_path / "fake_engine"
    fake.write_text(FAKE.format(py=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return Settings(state_dir=tmp_path / "state", science_root=REPO_ROOT, sim_engine=fake, sim_runs=tmp_path / "none",
                    research_python=tmp_path / "none", frontend_dist=tmp_path / "none", poll_s=0.05, min_available_memory_gb=0, cancel_grace_s=2)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def scenario(client):
    def make(hours=4, name="s", **kw):
        r = client.post("/api/scenarios", json={"name": name, "profile": "demo_synthetic", "params": {"hours": hours, **kw}})
        assert r.status_code == 201, r.text
        return r.json()
    return make
