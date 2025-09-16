#!/usr/bin/env python3
"""
Unified seed script for all rule data with proper execution order.

This script ensures proper seeding order to avoid conflicts:
1. Initialize database tables
2. Seed degree equivalencies (general)
3. Seed China/India specific rules (overwrites general for those countries)
4. Seed English language rules
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import Base, engine
from app.models import *  # Import all models to ensure they're registered

def init_database():
    """Initialize database tables"""
    print("Step 1: Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

def seed_degree_equivalencies():
    """Seed general degree equivalencies"""
    print("Step 2: Seeding general degree equivalencies...")
    try:
        # Import and run the degree equivalencies seeder
        from seed_degree_equivalencies import main as seed_degrees
        seed_degrees()
        print("General degree equivalencies seeded successfully")
    except Exception as e:
        print(f"Error seeding degree equivalencies: {e}")
        raise

def seed_china_india_rules():
    """Seed China and India specific rules (overwrites general rules)"""
    print("Step 3: Seeding China and India specific rules...")
    try:
        # Import and run the China/India seeder
        from seed_china_india_rules import main as seed_china_india
        seed_china_india()
        print("China and India specific rules seeded successfully")
    except Exception as e:
        print(f"Error seeding China/India rules: {e}")
        raise

def seed_english_rules():
    """Seed English language rules"""
    print("Step 4: Seeding English language rules...")
    try:
        # Import and run the English rules seeder
        from seed_english_rules_full import main as seed_english
        seed_english()
        print("English language rules seeded successfully")
    except Exception as e:
        print(f"Error seeding English rules: {e}")
        raise

def main():
    """Main function to run all seeding in correct order"""
    print("Starting complete database seeding process...")
    print("=" * 50)

    try:
        # Step 1: Initialize database
        init_database()
        print()

        # Step 2: Seed general degree equivalencies first
        seed_degree_equivalencies()
        print()

        # Step 3: Seed China/India specific rules (these will overwrite general rules for CHN/IND)
        seed_china_india_rules()
        print()

        # Step 4: Seed English rules (independent of degree rules)
        seed_english_rules()
        print()

        print("=" * 50)
        print("All seeding completed successfully!")
        print()
        print("Summary:")
        print("- Database tables initialized")
        print("- General degree equivalencies loaded")
        print("- China/India specific rules applied")
        print("- English language rules configured")

    except Exception as e:
        print(f"Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()