"""Persistent records: saved scenarios and immutable records of runs."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    profile: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict] = mapped_column(JSON)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)  # reproducible baselines cannot be edited
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(160))
    origin: Mapped[str] = mapped_column(String(20))  # platform | imported
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True)
    profile: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict] = mapped_column(JSON)
    data_class: Mapped[str] = mapped_column(String(30))  # synthetic | proprietary-derived
    status: Mapped[str] = mapped_column(String(20), index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_dir: Mapped[str] = mapped_column(Text)
    basename: Mapped[str] = mapped_column(String(80))
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    output_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
