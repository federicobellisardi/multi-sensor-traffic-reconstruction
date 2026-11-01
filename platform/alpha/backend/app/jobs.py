"""Job runner: one worker thread starting sim_engine processes under resource limits.

The engine is an independent executable: it receives a JSON file and writes files in its run
directory; this module knows only its exit code, its .status file and its _uniq_ output.
"""
import hashlib
import json
import logging
import os
import resource
import shutil
import signal
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psutil
from sqlalchemy import select

from . import profiles as P
from .config import REPO_ROOT, Settings
from .models import Run, now

log = logging.getLogger("alpha.jobs")
ACTIVE = ("queued", "running", "cancelling")
BRIDGE = Path(__file__).parent / "bridge" / "build_research_config.py"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_commit(root: Path) -> str | None:
    try:
        rev = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "minimocas", "model/analysis", "vars"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return rev + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def read_progress(status_file: Path) -> float | None:
    """Last line of the engine's status file: index;niter;datetime."""
    try:
        with open(status_file, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 200))
            line = f.read().decode(errors="replace").strip().splitlines()[-1]
        i, n, _ = line.split(";", 2)
        return min(int(i) / int(n), 1.0)
    except (OSError, ValueError, IndexError, ZeroDivisionError):
        return None


def tail(path: Path, lines: int = 200) -> list[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            return f.read().decode(errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def find_output(run_dir: Path, basename: str) -> Path | None:
    return next(iter(sorted(run_dir.glob(f"{basename}_uniq_*.csv"))), None)


class QueueFull(Exception):
    pass


class JobManager:
    def __init__(self, settings: Settings, session_factory):
        self.s = settings
        self.sessions = session_factory
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="alpha-jobs", daemon=True)
        self._procs: dict[str, subprocess.Popen] = {}
        self._deadlines: dict[str, float] = {}
        self._waiting_reason: str | None = None

    # ------------------------------------------------------------ lifecycle
    def start(self):
        self.recover()
        self._thread.start()

    def stop(self):
        """The server stops: running engines are terminated and marked interrupted, queued runs stay queued."""
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=self.s.cancel_grace_s + 5)

    def recover(self):
        """After a restart no engine is supervised: stop survivors of this platform and record the interruption."""
        with self.sessions() as db:
            for run in db.scalars(select(Run).where(Run.status.in_(["running", "cancelling"]))):
                self._kill_orphan(run)
                run.status = "cancelled" if run.cancel_requested else "failed"
                run.error = None if run.cancel_requested else "interrupted: the platform stopped while the run was active"
                run.finished_at = now()
                run.pid = None
            db.commit()

    def _kill_orphan(self, run: Run):
        if not run.pid:
            return
        try:
            p = psutil.Process(run.pid)
            # pid reuse guard: only a process with this run's configuration
            if any(run.run_dir in a for a in p.cmdline()):
                os.killpg(run.pid, signal.SIGKILL)
        except (psutil.Error, ProcessLookupError, PermissionError):
            pass

    # ------------------------------------------------------------ requests
    def submit(self, db, profile: str, params: P.ProfileParams, label: str, scenario_id: int | None) -> Run:
        n = len(db.scalars(select(Run).where(Run.status == "queued")).all())
        if n >= self.s.max_queued:
            raise QueueFull(f"queue full ({n} runs waiting)")
        run_id = f"r{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        run = Run(id=run_id, label=label, origin="platform", scenario_id=scenario_id, profile=profile,
                  params=params.model_dump(mode="json"), data_class=P.DATA_CLASS[profile], status="queued",
                  run_dir=str(self.s.runs_dir / run_id), basename="sim", seed=params.seed if params.seed is not None else 1,
                  cancel_requested=False, progress=0.0)
        db.add(run)
        db.commit()
        self._wake.set()
        return run

    def cancel(self, db, run: Run) -> Run:
        if run.status == "queued":
            run.status, run.finished_at = "cancelled", now()
        elif run.status in ("running", "cancelling"):
            run.status, run.cancel_requested = "cancelling", True
        db.commit()
        self._wake.set()
        return run

    def status_note(self) -> str | None:
        return self._waiting_reason

    # ------------------------------------------------------------ worker
    def _loop(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                log.exception("job loop error")
            self._wake.wait(self.s.poll_s)
            self._wake.clear()
        for run_id, proc in list(self._procs.items()):
            self._terminate(proc)
            self._finish(run_id, proc, interrupted=True)

    def _tick(self):
        for run_id, proc in list(self._procs.items()):
            self._supervise(run_id, proc)
        if len(self._procs) >= self.s.max_concurrent:
            return
        with self.sessions() as db:
            run = db.scalars(select(Run).where(Run.status == "queued").order_by(Run.created_at)).first()
            if run is None:
                self._waiting_reason = None
                return
            reason = self._blocked_by_resources()
            self._waiting_reason = reason
            if reason:
                return
            self._launch(db, run)

    def _blocked_by_resources(self) -> str | None:
        free = psutil.virtual_memory().available / 2**30
        if free < self.s.min_available_memory_gb:
            return f"waiting for memory: {free:.1f} GB available, {self.s.min_available_memory_gb} GB required"
        self.s.state_dir.mkdir(parents=True, exist_ok=True)
        disk = shutil.disk_usage(self.s.state_dir).free / 2**30
        if disk < self.s.min_free_disk_gb:
            return f"waiting for disk: {disk:.1f} GB free, {self.s.min_free_disk_gb} GB required"
        return None

    def _limits(self):
        limit = int(self.s.run_memory_limit_gb * 2**30)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        os.nice(self.s.engine_nice)

    def _launch(self, db, run: Run):
        run_dir = Path(run.run_dir)
        run_dir.mkdir(parents=True)
        cfg_path = run_dir / f"{run.basename}.json"
        base = str(run_dir / run.basename)
        env = dict(os.environ, OMP_NUM_THREADS=str(self.s.engine_threads))
        try:
            if not Path(self.s.sim_engine).is_file():
                raise RuntimeError(f"sim_engine not found: {self.s.sim_engine}; build it with hpc/setup.sh")
            params = P.validate_params(run.profile, run.params)
            if run.profile == "demo_synthetic":
                json.dump(P.demo_config(params, self.s, base), open(cfg_path, "w"), indent=1)
            else:
                missing = P.research_missing_inputs(self.s)
                if missing:
                    raise RuntimeError(f"research inputs missing: {missing}")
                req = run_dir / "request.json"
                json.dump(P.research_request(params, base), open(req, "w"), indent=1)
                # geopandas and pandas of the research environment, with the same paths as the analysis
                b = subprocess.run([str(self.s.research_python), str(BRIDGE), str(self.s.science_root), str(req), str(cfg_path)],
                                   capture_output=True, text=True, timeout=600, env=dict(env, SIM_RUNS=str(self.s.sim_runs), SIM_ENGINE=str(self.s.sim_engine)))
                if b.returncode:
                    raise RuntimeError("configuration failed: " + b.stderr[-1500:])
            run.config_sha256 = P.resolved_config_sha(cfg_path)
            run.engine_sha256 = sha256_file(self.s.sim_engine)
            run.git_commit = git_commit(self.s.science_root)
            self._write_manifest(run)
            db.commit()
            logf = open(run_dir / f"{run.basename}.log", "w")
            proc = subprocess.Popen([str(self.s.sim_engine), str(cfg_path)], cwd=run_dir, stdout=logf, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=env, start_new_session=True, preexec_fn=self._limits)
            logf.close()
        except Exception as e:
            run.status, run.error, run.finished_at = "failed", str(e)[:4000], now()
            db.commit()
            return
        db.refresh(run)  # a cancel may have arrived during the configuration step
        run.pid, run.started_at = proc.pid, now()
        if run.status == "queued":
            run.status = "running"
        else:
            run.status, run.cancel_requested, run.finished_at = "cancelling", True, None
        db.commit()
        self._procs[run.id] = proc
        self._deadlines[run.id] = time.monotonic() + self.s.run_timeout_s

    def _write_manifest(self, run: Run):
        (Path(run.run_dir) / "manifest.json").write_text(json.dumps({
            "run_id": run.id, "profile": run.profile, "params": run.params, "data_class": run.data_class, "seed": run.seed,
            "config_sha256": run.config_sha256, "engine": str(self.s.sim_engine), "engine_sha256": run.engine_sha256,
            "git_commit": run.git_commit, "platform_root": str(REPO_ROOT), "science_root": str(self.s.science_root),
            "frozen_model": P.is_frozen(run.profile, P.validate_params(run.profile, run.params)),
        }, indent=1))

    def _terminate(self, proc: subprocess.Popen):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(self.s.cancel_grace_s)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        except ProcessLookupError:
            pass

    def _supervise(self, run_id: str, proc: subprocess.Popen):
        with self.sessions() as db:
            run = db.get(Run, run_id)
            cancel = run.cancel_requested
            p = read_progress(Path(run.run_dir) / f"{run.basename}.status")
            if p is not None:
                run.progress = p
                db.commit()
        if cancel and proc.poll() is None:
            self._terminate(proc)
        if proc.poll() is not None:
            self._finish(run_id, proc)
        elif time.monotonic() > self._deadlines[run_id]:
            self._terminate(proc)
            self._finish(run_id, proc, timed_out=True)

    def _finish(self, run_id, proc, interrupted=False, timed_out=False):
        self._procs.pop(run_id, None)
        self._deadlines.pop(run_id, None)
        with self.sessions() as db:
            run = db.get(Run, run_id)
            run_dir, rc = Path(run.run_dir), proc.returncode
            output = find_output(run_dir, run.basename)
            run.pid, run.finished_at = None, now()
            if run.cancel_requested:
                run.status = "cancelled"
            elif interrupted:
                run.status, run.error = "failed", "interrupted: the platform stopped while the run was active"
            elif timed_out:
                run.status, run.error = "failed", f"timeout: exceeded {self.s.run_timeout_s} s"
            elif rc == 0 and output is not None:
                # sim_engine catches its exceptions and exits with 0: the output file decides, as in demand_scaling.run
                run.status, run.progress, run.output_sha256 = "completed", 1.0, sha256_file(output)
            else:
                last = tail(run_dir / f"{run.basename}.log", 8)
                run.status = "failed"
                run.error = f"engine exit code {rc}, no flow output. Last log lines:\n" + "\n".join(last)
            db.commit()
