"""Products endpoint backed by SQLite."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.database import get_connection

router = APIRouter(tags=["business"])


class Product(BaseModel):
    """A product row."""

    id: int
    name: str
    category: str
    price: float
    stock: int


@router.get("/products", response_model=list[Product])
def list_products() -> list[Product]:
    """Return products stored in the SQLite database."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, category, price, stock FROM products ORDER BY id"
        ).fetchall()
    return [Product(**dict(row)) for row in rows]