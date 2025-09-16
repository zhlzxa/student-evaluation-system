#!/usr/bin/env python3
"""
Database initialization script for production deployment
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.db.session import Base
from app.config import get_settings
from app.models import *  # Import all models to ensure they're registered

def init_database():
    """Initialize the database with all tables"""
    settings = get_settings()

    print("Initializing database...")
    print(f"Database URL: {settings.database_url}")

    # Create engine
    engine = create_engine(settings.database_url)

    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    # Run any custom initialization
    with engine.connect() as conn:
        # Enable UUID extension if needed
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            conn.commit()
            print("UUID extension enabled")
        except Exception as e:
            print(f"UUID extension setup: {e}")

    print("Database initialization completed!")

if __name__ == "__main__":
    init_database()