"""Sample users endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["business"])


class User(BaseModel):
    """A sample user."""

    id: int
    name: str
    email: str
    role: str
    active: bool


USERS: list[User] = [
    User(id=1, name="Asha Rao", email="asha.rao@example.com", role="admin", active=True),
    User(id=2, name="Liam Chen", email="liam.chen@example.com", role="editor", active=True),
    User(id=3, name="Maria Garcia", email="maria.garcia@example.com", role="viewer", active=True),
    User(id=4, name="Noah Smith", email="noah.smith@example.com", role="viewer", active=False),
    User(id=5, name="Priya Nair", email="priya.nair@example.com", role="editor", active=True),
]


@router.get("/users", response_model=list[User])
async def list_users() -> list[User]:
    """Return sample user data."""
    return USERS