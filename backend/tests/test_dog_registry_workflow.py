import sys
import os
import io
import time
from PIL import Image

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fastapi.testclient import TestClient
from db.database import SessionLocal
from db.models import Dog, User

import unittest

def run_full_dog_registry_workflow():
    print("\n=======================================================")
    print("STARTING E2E DOG REGISTRY WORKFLOW & AUDIT TEST")
    print("=======================================================")

    with TestClient(app) as client:
        # Step 0: Create and authenticate a test citizen user
        ts = int(time.time() * 1000)
        username = f"reg_tester_{ts}"
        email = f"tester_{ts}@streetpaw.org"
        password = "SecurePassword123!"

        signup_resp = client.post("/api/auth/signup", json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": "Registry Tester"
        })
        assert signup_resp.status_code in [200, 201], f"Signup failed: {signup_resp.text}"

        login_resp = client.post("/api/auth/login", json={
            "username_or_email": email,
            "password": password
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✓ Authenticated test user '{username}' successfully.")

        # -------------------------------------------------------------
        # SCAN 1: test_dog.jpg -> AI prediction kept (breed_source = 'ai')
        # -------------------------------------------------------------
        print("\n--- SCAN 1: Processing test_dog.jpg ---")
        dog1_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_dog.jpg")
        with open(dog1_path, "rb") as f:
            det1_resp = client.post("/api/detect", files={"file": ("test_dog.jpg", f, "image/jpeg")})
        assert det1_resp.status_code == 200, f"Detect 1 failed: {det1_resp.text}"
        det1_data = det1_resp.json()
        assert len(det1_data.get("detections", [])) > 0, "No detection for test_dog.jpg"
        d1 = det1_data["detections"][0]
        assert d1["species"] == "Dog", f"Expected Dog, got {d1['species']}"
        
        breed_1 = d1["breed"]
        breed_conf_1 = d1.get("breed_confidence", 0.0)
        disease_1 = d1.get("disease", "Normal")
        disease_conf_1 = d1.get("disease_confidence", 0.0)
        crop_1 = d1.get("roi_crop")
        print(f"✓ Scan 1 Results: Species={d1['species']}, Breed={breed_1} ({breed_conf_1:.1f}%), Disease={disease_1}")

        # Save to Registry: User accepts AI prediction without edit
        reg1_resp = client.post("/api/dogs/", headers=headers, json={
            "name": "Tommy Scan 1",
            "species": "Dog",
            "breed": breed_1,
            "breed_source": "ai",
            "sex": "male",
            "approx_age": "3 years",
            "colour_markings": "Golden Brown Coat",
            "sterilised": "yes",
            "ear_notch": True,
            "status": "Healthy / Sterilized",
            "health_status": "Healthy / Sterilized",
            "disease_name": disease_1,
            "disease_confidence": disease_conf_1,
            "image_url": crop_1 or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
            "location": "Kudlu Gate, Bengaluru",
            "location_lat": 12.8890,
            "location_lng": 77.6390
        })
        assert reg1_resp.status_code in [200, 201], f"Registration 1 failed: {reg1_resp.text}"
        dog1_record = reg1_resp.json()
        assert dog1_record["breed"] == breed_1
        assert dog1_record["breed_source"] == "ai"
        assert dog1_record["disease_name"] == disease_1
        print(f"✓ Dog 1 registered with Public Code: {dog1_record['public_code']}, Breed: {dog1_record['breed']}, Source: {dog1_record['breed_source']}")

        # -------------------------------------------------------------
        # SCAN 2: test_dog2.jpg -> User edits breed (breed_source = 'human')
        # -------------------------------------------------------------
        print("\n--- SCAN 2: Processing test_dog2.jpg ---")
        dog2_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_dog2.jpg")
        with open(dog2_path, "rb") as f:
            det2_resp = client.post("/api/detect", files={"file": ("test_dog2.jpg", f, "image/jpeg")})
        assert det2_resp.status_code == 200, f"Detect 2 failed: {det2_resp.text}"
        det2_data = det2_resp.json()
        assert len(det2_data.get("detections", [])) > 0, "No detection for test_dog2.jpg"
        d2 = det2_data["detections"][0]
        assert d2["species"] == "Dog", f"Expected Dog, got {d2['species']}"

        raw_breed_2 = d2["breed"]
        crop_2 = d2.get("roi_crop")
        disease_2 = d2.get("disease", "Normal")
        print(f"✓ Scan 2 Results: Species={d2['species']}, AI Raw Breed={raw_breed_2}, Disease={disease_2}")

        # Human in the loop correction: User changes breed to 'Indian Pariah / Desi'
        user_edited_breed = "Indian Pariah / Desi"
        computed_source = "ai" if user_edited_breed.lower() == (raw_breed_2 or "").lower() else "human"
        assert computed_source == "human", f"Expected breed_source to be 'human' after edit"

        reg2_resp = client.post("/api/dogs/", headers=headers, json={
            "name": "Desi Sheru",
            "species": "Dog",
            "breed": user_edited_breed,
            "breed_source": computed_source,
            "sex": "female",
            "approx_age": "1.5 years",
            "colour_markings": "White with Black spots",
            "sterilised": "no",
            "ear_notch": False,
            "status": "Healthy / Sterilized",
            "health_status": "Healthy / Sterilized",
            "disease_name": disease_2,
            "disease_confidence": d2.get("disease_confidence", 0.0),
            "image_url": crop_2 or "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=400&auto=format&fit=crop",
            "location": "Indiranagar 100ft Road, Bengaluru",
            "location_lat": 12.9716,
            "location_lng": 77.6412
        })
        assert reg2_resp.status_code in [200, 201], f"Registration 2 failed: {reg2_resp.text}"
        dog2_record = reg2_resp.json()
        assert dog2_record["breed"] == "Indian Pariah / Desi"
        assert dog2_record["breed_source"] == "human"
        print(f"✓ Dog 2 registered with Public Code: {dog2_record['public_code']}, Breed: {dog2_record['breed']}, Source: {dog2_record['breed_source']} (Human-in-the-loop edit confirmed)")

        # -------------------------------------------------------------
        # SCAN 3: test_dog3.jpg -> Third distinct scan (verifying no state leakage)
        # -------------------------------------------------------------
        print("\n--- SCAN 3: Processing test_dog3.jpg ---")
        dog3_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_dog3.jpg")
        with open(dog3_path, "rb") as f:
            det3_resp = client.post("/api/detect", files={"file": ("test_dog3.jpg", f, "image/jpeg")})
        assert det3_resp.status_code == 200, f"Detect 3 failed: {det3_resp.text}"
        det3_data = det3_resp.json()
        assert len(det3_data.get("detections", [])) > 0, "No detection for test_dog3.jpg"
        d3 = det3_data["detections"][0]
        assert d3["species"] == "Dog", f"Expected Dog, got {d3['species']}"

        breed_3 = d3["breed"]
        crop_3 = d3.get("roi_crop")
        disease_3 = d3.get("disease", "Normal")
        print(f"✓ Scan 3 Results: Species={d3['species']}, Breed={breed_3}, Disease={disease_3}")

        # Ensure Scan 3 data did not leak from Scan 1 or Scan 2
        assert crop_3 != crop_1, "Data leakage detected: Crop 3 is identical to Crop 1"
        assert crop_3 != crop_2, "Data leakage detected: Crop 3 is identical to Crop 2"

        reg3_resp = client.post("/api/dogs/", headers=headers, json={
            "name": "Stray Three",
            "species": "Dog",
            "breed": breed_3,
            "breed_source": "ai",
            "sex": "unknown",
            "approx_age": "2 years",
            "colour_markings": "Brown / Black mix",
            "sterilised": "unknown",
            "ear_notch": False,
            "status": "Healthy / Sterilized",
            "health_status": "Healthy / Sterilized",
            "disease_name": disease_3,
            "disease_confidence": d3.get("disease_confidence", 0.0),
            "image_url": crop_3 or "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&auto=format&fit=crop",
            "location": "Koramangala 4th Block, Bengaluru",
            "location_lat": 12.9352,
            "location_lng": 77.6245
        })
        assert reg3_resp.status_code in [200, 201], f"Registration 3 failed: {reg3_resp.text}"
        dog3_record = reg3_resp.json()
        assert dog3_record["breed"] == breed_3
        assert dog3_record["breed_source"] == "ai"
        print(f"✓ Dog 3 registered with Public Code: {dog3_record['public_code']}, Breed: {dog3_record['breed']}, Source: {dog3_record['breed_source']}")

        # -------------------------------------------------------------
        # NON-DOG REJECTION: test_cat.jpg
        # -------------------------------------------------------------
        print("\n--- NON-DOG VALIDATION: test_cat.jpg ---")
        cat_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_cat.jpg")
        with open(cat_path, "rb") as f:
            det_cat_resp = client.post("/api/detect", files={"file": ("test_cat.jpg", f, "image/jpeg")})
        assert det_cat_resp.status_code == 200
        cat_data = det_cat_resp.json()
        assert len(cat_data.get("detections", [])) > 0
        d_cat = cat_data["detections"][0]
        assert d_cat["species"] == "Cat", f"Expected Cat, got {d_cat['species']}"
        assert d_cat["breed"] is None, "Cat should NOT have a dog breed classification"
        assert d_cat["disease_status"] == "not_applicable", "Cat should NOT have dog disease profiling"
        print(f"✓ Vision Engine correctly classified species as Cat with locked breed/disease models.")

        # Attempt to save non-dog to Dog Registry
        cat_reg_resp = client.post("/api/dogs/", headers=headers, json={
            "name": "Kitty Non-Dog",
            "species": "Cat",
            "breed": "Persian",
            "image_url": "https://example.com/cat.jpg"
        })
        assert cat_reg_resp.status_code == 400, f"Expected HTTP 400 for non-dog species, got {cat_reg_resp.status_code}"
        assert "canine records only" in cat_reg_resp.json()["detail"].lower()
        print(f"✓ Dog Registry strictly rejected non-dog species with HTTP 400: '{cat_reg_resp.json()['detail']}'")

        # -------------------------------------------------------------
        # DATABASE PERSISTENCE VERIFICATION
        # -------------------------------------------------------------
        print("\n--- DATABASE DIRECT AUDIT ---")
        db = SessionLocal()
        try:
            d1_db = db.query(Dog).filter(Dog.public_code == dog1_record["public_code"]).first()
            assert d1_db is not None
            assert d1_db.breed == breed_1
            assert d1_db.breed_source == "ai"
            assert d1_db.species == "Dog"

            d2_db = db.query(Dog).filter(Dog.public_code == dog2_record["public_code"]).first()
            assert d2_db is not None
            assert d2_db.breed == "Indian Pariah / Desi"
            assert d2_db.breed_source == "human"
            assert d2_db.species == "Dog"

            d3_db = db.query(Dog).filter(Dog.public_code == dog3_record["public_code"]).first()
            assert d3_db is not None
            assert d3_db.breed == breed_3
            assert d3_db.breed_source == "ai"
            assert d3_db.species == "Dog"

            print(f"✓ Database verified:")
            print(f"   [Dog 1] {d1_db.public_code}: Breed={d1_db.breed}, BreedSource={d1_db.breed_source}, Disease={d1_db.disease_name}")
            print(f"   [Dog 2] {d2_db.public_code}: Breed={d2_db.breed}, BreedSource={d2_db.breed_source}, Disease={d2_db.disease_name}")
            print(f"   [Dog 3] {d3_db.public_code}: Breed={d3_db.breed}, BreedSource={d3_db.breed_source}, Disease={d3_db.disease_name}")

            # Clean up test records
            from db.models import DogLocation, Vaccination
            for d in [d1_db, d2_db, d3_db]:
                if d:
                    db.query(DogLocation).filter(DogLocation.dog_id == d.id).delete()
                    db.query(Vaccination).filter(Vaccination.dog_id == d.id).delete()
                    db.delete(d)
            db.query(User).filter(User.username == username).delete()
            db.commit()
            print("✓ Test artifacts cleaned up from database.")
        finally:
            db.close()

    print("\n=======================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! ZERO DATA LEAKAGE.")
    print("=======================================================\n")

class DogRegistryWorkflowTest(unittest.TestCase):
    def test_e2e_dog_registry(self):
        run_full_dog_registry_workflow()

if __name__ == "__main__":
    unittest.main()
