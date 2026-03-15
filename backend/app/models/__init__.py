"""Model package for Alembic autogenerate discovery.

Import concrete model modules here as they are added so Alembic can load them
before inspecting ``Base.metadata``.
"""

from app.core.database import Base

__all__ = ["Base"]
