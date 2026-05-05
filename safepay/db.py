"""
safepay/db.py
─────────────────────────────────────────────────────────────────────────────
Capa de base de datos para SafePay PRO.

- Producción  → PostgreSQL  (DATABASE_URL=postgresql://...)
- Desarrollo  → SQLite      (fallback automático)

Render entrega DATABASE_URL con prefijo postgres:// — se corrige aquí.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, text

# ── Engine ────────────────────────────────────────────────────────────────────
_raw_url = os.getenv("DATABASE_URL", "")

# Render usa postgres:// — SQLAlchemy necesita postgresql://
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

if _raw_url.startswith("postgresql://"):
    engine = create_engine(
        _raw_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    DB_BACKEND = "postgresql"
else:
    _data_dir = Path(__file__).parent / "data"
    _data_dir.mkdir(exist_ok=True)
    engine = create_engine(
        f"sqlite:///{_data_dir}/safepay.db",
        connect_args={"check_same_thread": False},
    )
    DB_BACKEND = "sqlite"

# ── Esquema ───────────────────────────────────────────────────────────────────
_CREATE_PAYMENTS = """
CREATE TABLE IF NOT EXISTS payments (
    id              TEXT PRIMARY KEY,
    amount          REAL    NOT NULL,
    currency        TEXT    NOT NULL DEFAULT 'PEN',
    method          TEXT    NOT NULL,
    description     TEXT,
    customer        TEXT,
    customer_email  TEXT,
    status          TEXT    NOT NULL DEFAULT 'pendiente',
    provider        TEXT    NOT NULL DEFAULT 'manual',
    payment_id      TEXT,
    transaction_id  TEXT,
    checkout_url    TEXT,
    metadata        TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
)
"""

_CREATE_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id          TEXT PRIMARY KEY,
    payment_id  TEXT NOT NULL,
    action      TEXT NOT NULL,
    notes       TEXT,
    created_at  TEXT NOT NULL
)
"""

# Columnas nuevas (v2 → se agregan si no existen en BD antigua)
_NEW_PAYMENT_COLS = [
    ("customer_email",  "TEXT"),
    ("provider",        "TEXT DEFAULT 'manual'"),
    ("payment_id",      "TEXT"),
    ("transaction_id",  "TEXT"),
    ("checkout_url",    "TEXT"),
]


def init_db() -> None:
    """Crea tablas si no existen."""
    with engine.begin() as conn:
        conn.execute(text(_CREATE_PAYMENTS))
        conn.execute(text(_CREATE_TRANSACTIONS))


def migrate_db() -> None:
    """Agrega columnas nuevas a tablas existentes (no destructivo)."""
    with engine.begin() as conn:
        for col_name, col_def in _NEW_PAYMENT_COLS:
            try:
                if DB_BACKEND == "postgresql":
                    conn.execute(text(
                        f"ALTER TABLE payments ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
                    ))
                else:
                    # SQLite no soporta IF NOT EXISTS en ALTER TABLE
                    conn.execute(text(
                        f"ALTER TABLE payments ADD COLUMN {col_name} {col_def}"
                    ))
            except Exception:
                pass  # La columna ya existe


def row_to_dict(row) -> dict:
    """Convierte una fila SQLAlchemy a dict."""
    if row is None:
        return {}
    import json
    d = dict(row._mapping)
    try:
        d["metadata"] = json.loads(d.get("metadata") or "{}")
    except (ValueError, TypeError):
        d["metadata"] = {}
    return d
