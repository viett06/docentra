"""Register all ORM tables before using Base.metadata, including in Alembic."""

import app.model  # noqa: F401
from app.db.base import Base as Base
