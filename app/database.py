"""SQLite persistence layer: schema, seed data and connection helper."""

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id      INTEGER PRIMARY KEY,
    name    TEXT    NOT NULL,
    email   TEXT    NOT NULL UNIQUE,
    role    TEXT    NOT NULL,
    active  INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS products (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    category  TEXT    NOT NULL,
    price     REAL    NOT NULL,
    stock     INTEGER NOT NULL DEFAULT 0
);
"""

SEED_USERS: list[tuple[int, str, str, str, int]] = [
    (1, "Asha Rao", "asha.rao@example.com", "admin", 1),
    (2, "Liam Chen", "liam.chen@example.com", "editor", 1),
    (3, "Maria Garcia", "maria.garcia@example.com", "viewer", 1),
    (4, "Noah Smith", "noah.smith@example.com", "viewer", 0),
    (5, "Priya Nair", "priya.nair@example.com", "editor", 1),
]

SEED_PRODUCTS: list[tuple[int, str, str, float, int]] = [
    (101, "Mechanical Keyboard", "accessories", 89.99, 42),
    (102, "27-inch Monitor", "displays", 279.5, 15),
    (103, "USB-C Dock", "accessories", 129.0, 30),
    (104, "Ergonomic Mouse", "accessories", 59.9, 77),
    (105, "Webcam 1080p", "video", 74.25, 0),
]

_init_lock = threading.Lock()
_initialised_path: str | None = None


def _connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create tables and seed them if empty. Safe to call repeatedly."""
    global _initialised_path
    path = get_settings().database_path
    with _init_lock:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        connection = _connect(path)
        try:
            connection.executescript(SCHEMA)
            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                connection.executemany(
                    "INSERT INTO users (id, name, email, role, active) "
                    "VALUES (?, ?, ?, ?, ?)",
                    SEED_USERS,
                )
            if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
                connection.executemany(
                    "INSERT INTO products (id, name, category, price, stock) "
                    "VALUES (?, ?, ?, ?, ?)",
                    SEED_PRODUCTS,
                )
            connection.commit()
        finally:
            connection.close()
        _initialised_path = path
        logger.info("database_initialised", path=path)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a short-lived connection, initialising the schema on first use."""
    path = get_settings().database_path
    if _initialised_path != path:
        init_db()
    connection = _connect(path)
    try:
        yield connection
    finally:
        connection.close()