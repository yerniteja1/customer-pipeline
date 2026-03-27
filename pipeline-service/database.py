import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── read connection string from environment ──
DATABASE_URL = os.environ.get(
    "DATABASE_URL"
)

# ── engine — one per process ──
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"}
)

# ── session factory ──
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ── base class for all ORM models ──
class Base(DeclarativeBase):
    pass


# ── dependency for FastAPI routes ──
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()