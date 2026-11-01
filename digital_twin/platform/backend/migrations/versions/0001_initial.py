"""Scenarios and runs."""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("profile", sa.String(40), nullable=False),
        sa.Column("params", sa.JSON, nullable=False),
        sa.Column("locked", sa.Boolean, nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("scenarios.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("scenario_id", sa.Integer, sa.ForeignKey("scenarios.id")),
        sa.Column("profile", sa.String(40), nullable=False),
        sa.Column("params", sa.JSON, nullable=False),
        sa.Column("data_class", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, index=True),
        sa.Column("progress", sa.Float, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("cancel_requested", sa.Boolean, nullable=False),
        sa.Column("pid", sa.Integer),
        sa.Column("run_dir", sa.Text, nullable=False),
        sa.Column("basename", sa.String(80), nullable=False),
        sa.Column("seed", sa.Integer),
        sa.Column("config_sha256", sa.String(64)),
        sa.Column("engine_sha256", sa.String(64)),
        sa.Column("git_commit", sa.String(60)),
        sa.Column("output_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("runs")
    op.drop_table("scenarios")
