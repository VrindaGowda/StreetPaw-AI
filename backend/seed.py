"""
StreetPaw.AI Standalone Database Seed Script
Run this script manually to populate the SQLite database (streetpaw.db) with initial demo records.
Command: python seed.py
"""

import sys
import os
import datetime

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import engine, SessionLocal, Base
from db.models import DogProfile, RescueCase

def run_seed():
    print("[INFO] Creating database schema tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Seed Dog Profiles
        dogs_count = db.query(DogProfile).count()
        if dogs_count == 0:
            print("[INFO] Seeding initial Dog Profiles...")
            seed_dogs = [
                DogProfile(
                    animal_id="DOG-1082",
                    species="Dog",
                    breed="Indian Pariah / Desi",
                    health_status="Healthy / Sterilized",
                    disease_name="Normal",
                    location="DSU Campus Gate 2, Bengaluru",
                    location_lat=12.9081,
                    location_lng=77.5653,
                    image_url="https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
                ),
                DogProfile(
                    animal_id="DOG-4921",
                    species="Dog",
                    breed="Street Mongrel",
                    health_status="Under Medical Care",
                    disease_name="Dermatitis Treated",
                    location="JP Nagar 6th Phase",
                    location_lat=12.9077,
                    location_lng=77.5857,
                    image_url="https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=400&auto=format&fit=crop",
                ),
                DogProfile(
                    animal_id="DOG-3310",
                    species="Dog",
                    breed="Indian Hound Mix",
                    health_status="Vaccinated",
                    disease_name="Normal",
                    location="Koramangala 4th Block",
                    location_lat=12.9345,
                    location_lng=77.6242,
                    image_url="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&auto=format&fit=crop",
                ),
                DogProfile(
                    animal_id="DOG-8842",
                    species="Dog",
                    breed="Indian breed",
                    health_status="Healthy",
                    disease_name="Normal",
                    location="Electronic City Phase 1",
                    location_lat=12.8399,
                    location_lng=77.6770,
                    image_url="https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=400&auto=format&fit=crop",
                ),
            ]
            db.add_all(seed_dogs)
            db.commit()
            print("[SUCCESS] Dog Profiles seeded successfully!")
        else:
            print(f"[INFO] Database already contains {dogs_count} Dog Profiles. Skipping dog seed.")

        # 2. Seed Rescue Cases
        rescues_count = db.query(RescueCase).count()
        if rescues_count == 0:
            print("[INFO] Seeding initial Rescue Cases...")
            seed_cases = [
                RescueCase(
                    ticket_id="RSC-9042",
                    title="Hit & Run Trauma Dog",
                    description="Severe leg injury near Hosur Road Flyover",
                    severity="CRITICAL",
                    status="PENDING DISPATCH",
                    landmark="DSU Main Gate 2",
                    latitude=12.9124,
                    longitude=77.5712,
                    reported_by="Citizen App (Redacted for Privacy)",
                    assigned_ngo="CUPA Rescue Squad #4",
                    photo_url="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&auto=format&fit=crop",
                ),
                RescueCase(
                    ticket_id="RSC-8812",
                    title="Severe Mange Lesions",
                    description="Demodicosis infection reported on 16th Main",
                    severity="HIGH",
                    status="AMBULANCE EN ROUTE",
                    landmark="BTM 2nd Stage Park",
                    latitude=12.9077,
                    longitude=77.5857,
                    reported_by="Citizen App (Redacted for Privacy)",
                    assigned_ngo="CUPA Rescue Squad #4",
                    photo_url="https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=400&auto=format&fit=crop",
                )
            ]
            db.add_all(seed_cases)
            db.commit()
            print("[SUCCESS] Rescue Cases seeded successfully!")
        else:
            print(f"[INFO] Database already contains {rescues_count} Rescue Cases. Skipping rescue seed.")

    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
