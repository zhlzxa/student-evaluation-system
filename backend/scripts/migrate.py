#!/usr/bin/env python3
"""
Database migration script for production deployment
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from alembic.config import Config
from alembic import command
from app.config import get_settings

def run_migrations():
    """Run database migrations"""
    settings = get_settings()

    print("Running database migrations...")
    print(f"Database URL: {settings.database_url}")

    # Set up Alembic configuration
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    # Run migrations
    try:
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()