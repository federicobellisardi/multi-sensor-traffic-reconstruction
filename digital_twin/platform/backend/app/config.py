"""Settings of the alpha platform. Everything is overridable by ALPHA_* variables (see README_ALPHA.md)."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, default))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALPHA_")

    # platform state: database and run directories; never inside the research outputs
    state_dir: Path = REPO_ROOT / ".work" / "alpha"
    # checkout holding the science code and private inputs (read only)
    science_root: Path = REPO_ROOT
    sim_engine: Path = _env_path("SIM_ENGINE", REPO_ROOT / ".work" / "build" / "sim_engine")
    research_python: Path = _env_path("PY", REPO_ROOT / ".work" / "env" / "bin" / "python")
    sim_runs: Path = _env_path("SIM_RUNS", REPO_ROOT / ".work" / "sim_runs")
    frontend_dist: Path = REPO_ROOT / "digital_twin" / "platform" / "frontend" / "dist"

    # resource limits of the job runner
    max_concurrent: int = 1
    max_queued: int = 10
    run_timeout_s: int = 3 * 3600
    run_memory_limit_gb: float = 6.0  # RLIMIT_AS of each engine process
    min_available_memory_gb: float = 3.0  # a queued run waits until this much memory is free
    min_free_disk_gb: float = 2.0
    engine_threads: int = 2
    engine_nice: int = 19
    cancel_grace_s: float = 10.0
    poll_s: float = 1.0

    @property
    def runs_dir(self) -> Path:
        return self.state_dir / "runs"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.state_dir / 'alpha.sqlite3'}"


def get_settings() -> Settings:
    return Settings()
