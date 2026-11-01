"""HTTP API of the alpha platform; also serves the built frontend. Bound to localhost by default: no authentication."""
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from . import db as dbm, jobs as J, network, profiles as P, results as R, schemas as S
from .config import Settings, get_settings
from .models import Run, Scenario

log = logging.getLogger("alpha")
DISCLAIMER = ("Research alpha. Outputs are raw simulator link flows, before detector correction; "
              "this is not a validated predictive digital twin.")
BASELINES = [
    ("Demo baseline (SYNTHETIC)", "Synthetic demand on the real public network, for testing the platform. Says nothing about real traffic.",
     "demo_synthetic", {"hours": 10, "trips_per_day": 20000}),
    ("Frozen model: Monday 10 Feb 2020", "The frozen research configuration (V6 route choice, calibrated k, province factors). Raw flows, before detector correction.",
     "research_frozen", {"variant": "V6_scaled", "day": "2020-02-10"}),
]
IMPORT_DIRS = ["demand/V6_scaled", "demand/V0_scaled"]


def seed_baselines(db):
    for name, desc, profile, params in BASELINES:
        if not db.scalar(select(Scenario).where(Scenario.name == name)):
            db.add(Scenario(name=name, description=desc, profile=profile, locked=True,
                            params=P.validate_params(profile, params).model_dump(mode="json")))
    db.commit()


def import_research_runs(db, s: Settings):
    """Register finished research simulations, read only and without copying. Their files are never modified."""
    for rel in IMPORT_DIRS:
        d = s.sim_runs / rel
        if not d.is_dir():
            continue
        variant = rel.rsplit("/", 1)[1]
        for cfg in sorted(d.glob("sim_*.json")):
            base = cfg.stem
            out = J.find_output(d, base)
            run_id = f"import-{variant}-{base}"
            if out is None or db.get(Run, run_id):
                continue
            tag = base.removeprefix("sim_")
            day = f"20{tag[:2]}-{tag[2:4]}-{tag[4:6]}"
            db.add(Run(id=run_id, label=f"Research output {variant} {day} (imported)", origin="imported", profile="research_frozen",
                       params={"variant": variant, "day": day}, data_class="proprietary-derived", status="completed", progress=1.0,
                       run_dir=str(d), basename=base, cancel_requested=False, config_sha256=P.resolved_config_sha(cfg), output_sha256=J.sha256_file(out)))
    db.commit()


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s.runs_dir.mkdir(parents=True, exist_ok=True)
        dbm.upgrade(s.database_url)
        with app.state.sessions() as db:
            seed_baselines(db)
            import_research_runs(db, s)
        app.state.jobs.start()
        yield
        app.state.jobs.stop()

    app = FastAPI(title="Regional mobility platform (alpha)", version="0.1.0-alpha", description=DISCLAIMER, lifespan=lifespan)
    s.state_dir.mkdir(parents=True, exist_ok=True)
    app.state.sessions = dbm.make_session_factory(s.database_url)
    app.state.jobs = J.JobManager(s, app.state.sessions)

    def get_db(request: Request):
        with request.app.state.sessions() as db:
            yield db

    def run_or_404(db, run_id: str) -> Run:
        run = db.get(Run, run_id)
        if run is None:
            raise HTTPException(404, f"run {run_id} not found")
        return run

    def scenario_or_404(db, sid: int) -> Scenario:
        sc = db.get(Scenario, sid)
        if sc is None:
            raise HTTPException(404, f"scenario {sid} not found")
        return sc

    def checked_params(profile: str, params: dict) -> P.ProfileParams:
        try:
            return P.validate_params(profile, params)
        except (ValidationError, ValueError) as e:
            detail = e.errors(include_context=False, include_url=False, include_input=False) if isinstance(e, ValidationError) else str(e)
            raise HTTPException(422, detail)

    def run_out(run: Run) -> S.RunOut:
        out = S.RunOut.model_validate(run)
        out.has_results = run.status == "completed" and J.find_output(Path(run.run_dir), run.basename) is not None
        try:
            out.frozen_model = run.origin == "imported" or P.is_frozen(run.profile, P.validate_params(run.profile, run.params))
        except ValueError:
            pass
        return out

    def flow_table(run: Run) -> R.FlowTable:
        path = J.find_output(Path(run.run_dir), run.basename) if run.status == "completed" else None
        if path is None:
            raise HTTPException(409, f"run {run.id} has no results (status {run.status})")
        return R.table(path)

    # ------------------------------------------------------------ system
    @app.get("/api/health", tags=["system"])
    def health(request: Request):
        return {"status": "ok", "version": app.version, "disclaimer": DISCLAIMER, "scheduler_note": request.app.state.jobs.status_note()}

    @app.get("/api/capabilities", tags=["system"])
    def caps():
        return P.capabilities(s)

    # ------------------------------------------------------------ network
    @app.get("/api/network", tags=["network"], summary="Road network as gzip-compressed GeoJSON (geometry simplified for display)")
    def net():
        return FileResponse(network.network_file(s.science_root, s.state_dir), media_type="application/geo+json", headers={"Content-Encoding": "gzip", "Cache-Control": "max-age=3600"})

    @app.get("/api/network/boundaries", tags=["network"], summary="Provincial boundaries")
    def boundaries():
        return FileResponse(s.science_root / network.SHAPES, media_type="application/geo+json")

    @app.get("/api/network/classes", tags=["network"])
    def classes():
        return network.CLASS_ORDER

    # ------------------------------------------------------------ scenarios
    @app.get("/api/scenarios", response_model=list[S.ScenarioOut], tags=["scenarios"])
    def list_scenarios(db=Depends(get_db)):
        return db.scalars(select(Scenario).order_by(Scenario.locked.desc(), Scenario.created_at.desc())).all()

    def save(db, sc):
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"a scenario named {sc.name!r} already exists")
        return sc

    @app.post("/api/scenarios", response_model=S.ScenarioOut, status_code=201, tags=["scenarios"])
    def create_scenario(body: S.ScenarioIn, db=Depends(get_db)):
        p = checked_params(body.profile, body.params)
        sc = Scenario(name=body.name, description=body.description, profile=body.profile, params=p.model_dump(mode="json"), locked=False)
        db.add(sc)
        return save(db, sc)

    @app.patch("/api/scenarios/{sid}", response_model=S.ScenarioOut, tags=["scenarios"])
    def patch_scenario(sid: int, body: S.ScenarioPatch, db=Depends(get_db)):
        sc = scenario_or_404(db, sid)
        if sc.locked:
            raise HTTPException(403, "baselines are locked; duplicate this scenario to change it")
        if body.params is not None:
            sc.params = checked_params(sc.profile, body.params).model_dump(mode="json")
        if body.name is not None:
            sc.name = body.name
        if body.description is not None:
            sc.description = body.description
        return save(db, sc)

    @app.post("/api/scenarios/{sid}/duplicate", response_model=S.ScenarioOut, status_code=201, tags=["scenarios"])
    def duplicate_scenario(sid: int, body: S.DuplicateIn, db=Depends(get_db)):
        src = scenario_or_404(db, sid)
        sc = Scenario(name=body.name, description=src.description, profile=src.profile, params=dict(src.params), locked=False, parent_id=src.id)
        db.add(sc)
        return save(db, sc)

    @app.post("/api/scenarios/{sid}/runs", response_model=S.RunOut, status_code=202, tags=["runs"], summary="Launch a run; parameters are snapshotted")
    def launch(sid: int, request: Request, db=Depends(get_db)):
        sc = scenario_or_404(db, sid)
        cap = P.capabilities(s)["profiles"][sc.profile]
        if not cap["available"]:
            raise HTTPException(409, f"profile {sc.profile} is not available here: {cap.get('missing_inputs') or 'sim_engine not found'}")
        try:
            run = request.app.state.jobs.submit(db, sc.profile, checked_params(sc.profile, sc.params), sc.name, sc.id)
        except J.QueueFull as e:
            raise HTTPException(429, str(e))
        return run_out(run)

    # ------------------------------------------------------------ runs
    @app.get("/api/runs", response_model=list[S.RunOut], tags=["runs"])
    def list_runs(status: str | None = None, db=Depends(get_db)):
        q = select(Run).order_by(Run.created_at.desc())
        if status:
            q = q.where(Run.status == status)
        return [run_out(r) for r in db.scalars(q)]

    @app.get("/api/runs/compare", tags=["results"], summary="Descriptive comparison of two runs (B minus A)")
    def compare(a: str, b: str, road_class: str | None = None, db=Depends(get_db)):
        ra, rb = run_or_404(db, a), run_or_404(db, b)
        ta, tb = flow_table(ra), flow_table(rb)
        mask = None
        if road_class:
            cl = network.road_classes(s.science_root)
            mask = np.array([cl.get(int(c), "unmatched") == road_class for c in ta.cids])
        try:
            res = R.compare(ta, tb, mask)
        except ValueError as e:
            raise HTTPException(409, str(e))
        warnings = []
        if ra.data_class != rb.data_class:
            warnings.append("one run is synthetic: the difference has no scientific meaning")
        if ra.params.get("day", "") != rb.params.get("day", "") and ra.profile == rb.profile:
            warnings.append("different days")
        if len(ta.times) != len(tb.times):
            warnings.append(f"different windows: only the first {res['common_hours']} hours are compared")
        return {**res, "a": a, "b": b, "warnings": warnings}

    @app.get("/api/runs/{run_id}", response_model=S.RunOut, tags=["runs"])
    def get_run(run_id: str, db=Depends(get_db)):
        return run_out(run_or_404(db, run_id))

    @app.post("/api/runs/{run_id}/cancel", response_model=S.RunOut, tags=["runs"])
    def cancel(run_id: str, request: Request, db=Depends(get_db)):
        run = run_or_404(db, run_id)
        if run.origin != "platform":
            raise HTTPException(409, "imported research runs are read only")
        if run.status not in J.ACTIVE:
            raise HTTPException(409, f"run is already {run.status}")
        return run_out(request.app.state.jobs.cancel(db, run))

    @app.get("/api/runs/{run_id}/logs", response_model=S.LogOut, tags=["runs"])
    def logs(run_id: str, lines: int = Query(200, ge=1, le=2000), db=Depends(get_db)):
        run = run_or_404(db, run_id)
        return S.LogOut(lines=J.tail(Path(run.run_dir) / f"{run.basename}.log", lines))

    @app.get("/api/runs/{run_id}/config", tags=["runs"], summary="Exact engine configuration of this run")
    def config(run_id: str, db=Depends(get_db)):
        run = run_or_404(db, run_id)
        f = Path(run.run_dir) / f"{run.basename}.json"
        if not f.is_file():
            raise HTTPException(404, "configuration not written yet")
        c = json.load(open(f))
        c["sources"] = {"count": len(c.get("sources", {})), "total_departures": sum(sum(v.get("creation_rate", [])) for v in c.get("sources", {}).values())}
        return c

    @app.get("/api/runs/{run_id}/flows", response_model=S.FlowsOut, tags=["results"], summary="Flow per link: one hour, or the sum over the window")
    def flows(run_id: str, hour: int | None = Query(None, ge=0, le=23), direction: Literal["both", "FT", "TF"] = "both", db=Depends(get_db)):
        t = flow_table(run_or_404(db, run_id))
        v = t.values(direction)
        if hour is not None and hour >= len(t.times):
            raise HTTPException(422, f"this run has only {len(t.times)} hours")
        col = v.sum(1) if hour is None else v[:, hour]
        return S.FlowsOut(run_id=run_id, hour=None if hour is None else t.times[hour], direction=direction, poly_cid=t.cids.tolist(), flow=col.tolist(), max_flow=float(col.max(initial=0)))

    @app.get("/api/runs/{run_id}/links/{poly_cid}", response_model=S.SeriesOut, tags=["results"], summary="Hourly flow of one road")
    def link(run_id: str, poly_cid: int, db=Depends(get_db)):
        t = flow_table(run_or_404(db, run_id))
        if poly_cid not in t.index:
            raise HTTPException(404, f"link {poly_cid} not in this run")
        i = t.index[poly_cid]
        return S.SeriesOut(run_id=run_id, poly_cid=poly_cid, hours=[x[11:16] for x in t.times], FT=t.ft[i].tolist(), TF=t.tf[i].tolist())

    @app.get("/api/runs/{run_id}/profile", response_model=S.ProfileOut, tags=["results"], summary="Network-wide hourly total, optionally for one road class")
    def profile(run_id: str, road_class: str | None = None, db=Depends(get_db)):
        run = run_or_404(db, run_id)
        t = flow_table(run)
        v = t.values()
        if road_class:
            cl = network.road_classes(s.science_root)
            v = v[np.array([cl.get(int(c), "unmatched") == road_class for c in t.cids])]
        partial = len(t.times) == 24 and run.profile == "research_frozen" and run.params.get("hours") is None
        return S.ProfileOut(run_id=run_id, hours=[x[11:16] for x in t.times], total=v.sum(0).tolist(), road_class=road_class, partial_last_hour=partial)

    # ------------------------------------------------------------ frontend
    dist = s.frontend_dist
    if (dist / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            return FileResponse(dist / "index.html")
    return app
