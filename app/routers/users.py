"""Users endpoint backed by SQLite."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import get_connection

router = APIRouter(tags=["business"])


class User(BaseModel):
    """A user row."""

    id: int
    name: str
    email: str
    role: str
    active: bool


@router.get("/users", response_model=list[User])
def list_users() -> list[User]:
    """Return users stored in the SQLite database."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, email, role, active FROM users ORDER BY id"
        ).fetchall()
    return [
        User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=row["role"],
            active=bool(row["active"]),
        )
        for row in rows
    ]