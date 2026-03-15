"""Model package for Alembic autogenerate discovery."""

from app.core.database import Base
from app.models.user import Document, StudentProfile, Subject, TeacherProfile, User

__all__ = [
    "Base",
    "Document",
    "StudentProfile",
    "Subject",
    "TeacherProfile",
    "User",
]
