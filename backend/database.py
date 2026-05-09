import logging

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

logger = logging.getLogger(__name__)

# Create database engine
if settings.database_url.startswith("sqlite"):
    # SQLite doesn't support connection pooling
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )
else:
    # PostgreSQL with connection pooling
    from sqlalchemy.pool import QueuePool

    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        echo=settings.debug,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables + migrate missing columns."""
    Base.metadata.create_all(bind=engine)
    _migrate_conversations_table()


def _migrate_conversations_table():
    """Add missing columns to conversations table (SQLite migration)."""
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            existing_cols = {c["name"] for c in inspector.get_columns("conversations")}

            # Columns that should exist per the model
            required_cols = {
                "tags": "TEXT",
                "category": "VARCHAR(50)",
                "summary": "TEXT",
            }

            for col_name, col_type in required_cols.items():
                if col_name not in existing_cols:
                    conn.execute(
                        text(
                            f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}"
                        )
                    )
                    conn.commit()
                    logger.info(
                        f"[Migration] Added conversations.{col_name} ({col_type})"
                    )

    except Exception as e:
        logger.warning(f"[Migration] conversations table migration skipped: {e}")
