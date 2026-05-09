"""
Initialize database with sample agents and migrate schema.

CLI entry point — delegates to seed.py for the actual seeding logic.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db
from seed import DEFAULT_AGENTS, ensure_agents_seeded, ensure_team_settings
from sqlalchemy import inspect as sa_inspect, text
from database import engine


def migrate_database():
    """Add new columns to agents table if they don't exist (SQLite + PostgreSQL compatible)."""
    print("Checking for schema migration...")

    inspector = sa_inspect(engine)
    existing_columns = {c["name"] for c in inspector.get_columns("agents")}

    # New columns to add
    new_columns = {
        "display_name": "VARCHAR(50)",
        "emoji": "VARCHAR(10)",
        "badge_text": "VARCHAR(20)",
        "icon": "VARCHAR(50)",
        "color": "VARCHAR(20)",
    }

    # Add missing columns
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
                    )
                    conn.commit()
                print(f"  ✓ Added column: {col_name}")
            except Exception as e:
                print(f"  ! Column {col_name} may already exist: {e}")

    print("✓ Migration complete")


def main():
    print("=" * 60)
    print("Initializing AI Virtual Company Database")
    print("=" * 60)

    # Step 1: Initialize database (create tables)
    init_db()
    print("✓ Database tables created/verified")

    # Step 2: Run migrations
    migrate_database()

    # Step 3: Seed agents (reuses shared seed.py logic)
    ensure_agents_seeded()
    print("✓ Agents seeded (or already present)")

    # Step 4: Seed team settings
    ensure_team_settings()
    print("✓ Team settings checked")

    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
