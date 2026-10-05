"""Sample products endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["business"])


class Product(BaseModel):
    """A sample product."""

    id: int
    name: str
    category: str
    price: float
    stock: int


PRODUCTS: list[Product] = [
    Product(id=101, name="Mechanical Keyboard", category="accessories", price=89.99, stock=42),
    Product(id=102, name="27-inch Monitor", category="displays", price=279.5, stock=15),
    Product(id=103, name="USB-C Dock", category="accessories", price=129.0, stock=30),
    Product(id=104, name="Ergonomic Mouse", category="accessories", price=59.9, stock=77),
    Product(id=105, name="Webcam 1080p", category="video", price=74.25, stock=0),
]


@router.get("/products", response_model=list[Product])
async def list_products() -> list[Product]:
    """Return sample product data."""
    return PRODUCTS