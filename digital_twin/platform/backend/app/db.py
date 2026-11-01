"""Database session and schema migrations (Alembic; applied automatically on startup)."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BACKEND = Path(__file__).resolve().parents[1]


class Base(DeclarativeBase):
    pass


def make_session_factory(url: str):
    # rollback journal: the state directory may be on NFS, where SQLite WAL is unsafe
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})
    return sessionmaker(engine, expire_on_commit=False)


def upgrade(url: str) -> None:
    cfg = Config()
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
