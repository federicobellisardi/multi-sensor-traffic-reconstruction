"""API and job runner, with a stand-in engine script. The real engine is covered by test_engine.py and the e2e suite."""
import json
import os
from pathlib import Path

import psutil
from fastapi.testclient import TestClient

from app.main import create_app
from conftest import wait


def launch(client, sc):
    r = client.post(f"/api/scenarios/{sc['id']}/runs")
    assert r.status_code == 202, r.text
    return r.json()


def test_health_and_docs(client):
    assert "not a validated" in client.get("/api/health").json()["disclaimer"]
    assert "/api/runs" in client.get("/openapi.json").json()["paths"]


def test_capabilities_report_missing_research_inputs(client):
    c = client.get("/api/capabilities").json()
    assert c["profiles"]["demo_synthetic"]["available"]
    assert not c["profiles"]["research_frozen"]["available"]
    assert c["profiles"]["research_frozen"]["missing_inputs"]
    assert not c["perturbations"]["road_closure"]["supported"]


def test_research_profile_refused_when_inputs_are_missing(client):
    sid = next(s["id"] for s in client.get("/api/scenarios").json() if s["profile"] == "research_frozen")
    r = client.post(f"/api/scenarios/{sid}/runs")
    assert r.status_code == 409 and "not available" in r.text


def test_validation_rejects_bad_parameters(client):
    post = lambda p, profile="demo_synthetic": client.post("/api/scenarios", json={"name": "x", "profile": profile, "params": p}).status_code
    assert post({"hours": 0}) == 422
    assert post({"hours": 4, "unknown": 1}) == 422
    assert post({"perturbations": [{"kind": "demand_scale", "factor": -1}]}) == 422
    assert post({"perturbations": [{"kind": "road_closure", "links": [1]}]}) == 422, "closures must not be accepted"
    assert post({"day": "2019-01-01"}, "research_frozen") == 422
    assert post({}, "nope") == 422


def test_baselines_are_locked_and_duplicates_are_editable(client):
    base = next(s for s in client.get("/api/scenarios").json() if s["profile"] == "demo_synthetic")
    assert base["locked"]
    assert client.patch(f"/api/scenarios/{base['id']}", json={"name": "x"}).status_code == 403
    dup = client.post(f"/api/scenarios/{base['id']}/duplicate", json={"name": "mine"})
    assert dup.status_code == 201 and not dup.json()["locked"] and dup.json()["parent_id"] == base["id"]
    assert client.post(f"/api/scenarios/{base['id']}/duplicate", json={"name": "mine"}).status_code == 409
    new = client.patch(f"/api/scenarios/{dup.json()['id']}", json={"params": {"hours": 2}})
    assert new.json()["params"]["hours"] == 2


def test_run_completes_with_traceability_and_results(client, scenario):
    sc = scenario(hours=5, seed=7)
    run = wait(client, launch(client, sc)["id"], ["completed", "failed"])
    assert run["status"] == "completed" and run["progress"] == 1 and run["seed"] == 7
    assert run["data_class"] == "synthetic" and not run["frozen_model"]
    assert all(run[k] for k in ("config_sha256", "engine_sha256", "output_sha256"))
    manifest = json.load(open(Path(run["run_dir"]) / "manifest.json"))
    assert manifest["run_id"] == run["id"] and manifest["params"]["seed"] == 7
    # both directions summed; hour 2: FT 3, TF 6
    f = client.get(f"/api/runs/{run['id']}/flows", params={"hour": 2}).json()
    assert f["poly_cid"] == [0, 23] and f["flow"] == [9, 9]
    assert client.get(f"/api/runs/{run['id']}/flows", params={"hour": 2, "direction": "TF"}).json()["flow"] == [6, 6]
    assert client.get(f"/api/runs/{run['id']}/flows", params={"hour": 9}).status_code == 422
    s = client.get(f"/api/runs/{run['id']}/links/23").json()
    assert s["FT"] == [1, 2, 3, 4, 5] and s["TF"] == [2, 4, 6, 8, 10] and s["hours"][0] == "00:00"
    assert client.get(f"/api/runs/{run['id']}/links/999").status_code == 404
    assert client.get(f"/api/runs/{run['id']}/profile").json()["total"] == [6, 12, 18, 24, 30]
    assert any("fake engine" in x for x in client.get(f"/api/runs/{run['id']}/logs").json()["lines"])


def test_snapshot_survives_scenario_edit(client, scenario):
    sc = scenario(hours=5)
    run = wait(client, launch(client, sc)["id"], ["completed"])
    client.patch(f"/api/scenarios/{sc['id']}", json={"params": {"hours": 6}})
    assert client.get(f"/api/runs/{run['id']}").json()["params"]["hours"] == 5


def test_exit_zero_without_output_is_a_failure(client, scenario):
    run = wait(client, launch(client, scenario(hours=1))["id"], ["completed", "failed"])
    assert run["status"] == "failed" and "boom" in run["error"]
    assert client.get(f"/api/runs/{run['id']}/flows").status_code == 409


def test_nonzero_exit_is_a_failure(client, scenario):
    run = wait(client, launch(client, scenario(hours=2))["id"], ["completed", "failed"])
    assert run["status"] == "failed" and "exit code 3" in run["error"]


def test_missing_engine_fails_cleanly(settings, tmp_path):
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {}}).json()
        settings.sim_engine.unlink()
        assert c.post(f"/api/scenarios/{sc['id']}/runs").status_code == 409


def test_cancel_running_kills_the_process(client, scenario):
    run = launch(client, scenario(hours=3))
    running = wait(client, run["id"], ["running"])
    pid = next(p.pid for p in psutil.Process().children(recursive=True) if any(running["run_dir"] in a for a in p.cmdline()))
    assert client.post(f"/api/runs/{run['id']}/cancel").json()["status"] in ("cancelling", "cancelled")
    done = wait(client, run["id"], ["cancelled"])
    assert done["finished_at"]
    assert not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    assert client.post(f"/api/runs/{run['id']}/cancel").status_code == 409


def test_cancel_during_launch_is_not_lost(settings, monkeypatch):
    """A cancel arriving while the configuration is being prepared must still stop the run."""
    from app import jobs as J
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {"hours": 3}}).json()
        real = J.git_commit
        holder = {}

        def slow(root):
            holder["cancel"] = c.post(f"/api/runs/{holder['id']}/cancel").status_code
            return real(root)
        monkeypatch.setattr(J, "git_commit", slow)
        mgr = c.app.state.jobs
        mgr._wake.clear()
        orig = mgr.submit

        def submit(db, *a):
            run = orig(db, *a)
            holder["id"] = run.id
            return run
        mgr.submit = submit
        run = c.post(f"/api/scenarios/{sc['id']}/runs").json()
        done = wait(c, run["id"], ["cancelled", "completed", "failed"])
        assert done["status"] == "cancelled" and holder["cancel"] == 200


def test_concurrency_limit_and_queue_cancel(client, scenario):
    a = launch(client, scenario(hours=3, name="a"))
    wait(client, a["id"], ["running"])
    b = launch(client, scenario(hours=3, name="b"))
    assert client.get(f"/api/runs/{b['id']}").json()["status"] == "queued"
    assert client.post(f"/api/runs/{b['id']}/cancel").json()["status"] == "cancelled"
    assert not Path(b["run_dir"]).exists(), "a run cancelled in the queue never started"
    client.post(f"/api/runs/{a['id']}/cancel")
    wait(client, a["id"], ["cancelled"])


def test_queue_is_bounded(settings, tmp_path):
    settings.max_queued = 1
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {"hours": 3}}).json()
        codes = [c.post(f"/api/scenarios/{sc['id']}/runs").status_code for _ in range(4)]
        assert 429 in codes
        for r in c.get("/api/runs").json():
            if r["status"] in ("queued", "running"):
                c.post(f"/api/runs/{r['id']}/cancel")
        for r in c.get("/api/runs").json():
            wait(c, r["id"], ["cancelled", "completed"])


def test_memory_gate_holds_runs_in_the_queue(settings):
    settings.min_available_memory_gb = 1e9
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {"hours": 5}}).json()
        run = c.post(f"/api/scenarios/{sc['id']}/runs").json()
        import time
        time.sleep(0.3)
        assert c.get(f"/api/runs/{run['id']}").json()["status"] == "queued"
        assert "memory" in c.get("/api/health").json()["scheduler_note"]
        c.post(f"/api/runs/{run['id']}/cancel")


def test_timeout_is_a_failure(settings):
    settings.run_timeout_s = 0
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {"hours": 3}}).json()
        run = c.post(f"/api/scenarios/{sc['id']}/runs").json()
        done = wait(c, run["id"], ["failed", "completed"])
        assert done["status"] == "failed" and "timeout" in done["error"]


def test_previous_runs_survive_restart_and_active_runs_are_marked(settings):
    with TestClient(create_app(settings)) as c:
        sc = c.post("/api/scenarios", json={"name": "s", "profile": "demo_synthetic", "params": {"hours": 5}}).json()
        done = wait(c, c.post(f"/api/scenarios/{sc['id']}/runs").json()["id"], ["completed"])
        sc3 = c.post("/api/scenarios", json={"name": "slow", "profile": "demo_synthetic", "params": {"hours": 3}}).json()
        active = c.post(f"/api/scenarios/{sc3['id']}/runs").json()
        wait(c, active["id"], ["running"])
    with TestClient(create_app(settings)) as c:
        assert c.get(f"/api/runs/{done['id']}").json()["status"] == "completed"
        assert c.get(f"/api/runs/{done['id']}/flows").status_code == 200
        r = c.get(f"/api/runs/{active['id']}").json()
        assert r["status"] == "failed" and "interrupted" in r["error"]


def test_compare_runs(client, scenario):
    a = wait(client, launch(client, scenario(hours=5, name="a"))["id"], ["completed"])
    b = wait(client, launch(client, scenario(hours=6, name="b"))["id"], ["completed"])
    r = client.get("/api/runs/compare", params={"a": a["id"], "b": b["id"]}).json()
    assert r["common_hours"] == 5 and r["relative_total_change"] == 0
    assert any("first 5 hours" in w for w in r["warnings"])


def test_imported_runs_are_read_only_and_files_untouched(settings):
    d = settings.sim_runs / "demand/V6_scaled"
    d.mkdir(parents=True)
    (d / "sim_200210.json").write_text('{"state_basename": "x", "sources": {}}')
    f = d / "sim_200210_uniq_200210_000000.csv"
    f.write_text("poly_lid;poly_cid;oneway;2020-02-10 00:00:00\n0;0;FT;5\n0;0;TF;6\n")
    (d / (f.name + ".corrected")).write_text("poly_lid;poly_cid;oneway;2020-02-10 00:00:00\n0;0;FT;999.5\n0;0;TF;999.5\n")
    before = f.read_bytes(), f.stat().st_mtime_ns
    with TestClient(create_app(settings)) as c:
        rid = "import-V6_scaled-sim_200210"
        r = c.get(f"/api/runs/{rid}").json()
        assert r["origin"] == "imported" and r["data_class"] == "proprietary-derived" and r["has_results"]
        assert c.get(f"/api/runs/{rid}/flows").json()["flow"] == [11]
        assert c.post(f"/api/runs/{rid}/cancel").status_code == 409
    assert (f.read_bytes(), f.stat().st_mtime_ns) == before


def test_network_matches_cartography(client):
    import gzip
    r = client.get("/api/network")
    g = r.json()
    assert len(g["features"]) == 3925
    assert {f["properties"]["road_class"] for f in g["features"]} >= {"motorway", "primary"}
    assert all(f["id"] == f["properties"]["poly_cid"] for f in g["features"])


def test_demo_demand_is_conserved_by_rounding(settings):
    from app import profiles as P
    c = P.demo_config(P.DemoParams(hours=2, trips_per_day=1000), settings, "x")
    total = sum(sum(s["creation_rate"]) for s in c["sources"].values())
    assert abs(total - 1000) <= len(c["sources"])
    assert all(len(s["creation_rate"]) == 96 for s in c["sources"].values())


def test_old_engine_without_seed_option_is_flagged(client):
    assert "no seed option" in client.get("/api/capabilities").json()["engine_warnings"][0]
