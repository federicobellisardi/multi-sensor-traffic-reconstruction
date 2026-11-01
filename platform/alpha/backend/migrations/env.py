from alembic import context
from sqlalchemy import create_engine

from app.db import Base
from app import models  # noqa: F401

url = context.config.get_main_option("sqlalchemy.url")
engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
