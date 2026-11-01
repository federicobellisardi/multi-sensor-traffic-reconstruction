"""Request and response schemas of the API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScenarioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field("", max_length=4000)
    profile: str
    params: dict = Field(default_factory=dict)


class ScenarioPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=4000)
    params: dict | None = None


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    profile: str
    params: dict
    locked: bool
    parent_id: int | None
    created_at: datetime
    updated_at: datetime


class DuplicateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    label: str
    origin: str
    scenario_id: int | None
    profile: str
    params: dict
    data_class: str
    status: str
    progress: float
    error: str | None
    seed: int | None
    config_sha256: str | None
    engine_sha256: str | None
    git_commit: str | None
    output_sha256: str | None
    run_dir: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    frozen_model: bool = False
    has_results: bool = False


class LogOut(BaseModel):
    lines: list[str]


class FlowsOut(BaseModel):
    run_id: str
    hour: str | None
    direction: str
    poly_cid: list[int]
    flow: list[float]
    max_flow: float


class SeriesOut(BaseModel):
    run_id: str
    poly_cid: int
    hours: list[str]
    FT: list[float]
    TF: list[float]


class ProfileOut(BaseModel):
    run_id: str
    hours: list[str]
    total: list[float]
    road_class: str | None
    partial_last_hour: bool
