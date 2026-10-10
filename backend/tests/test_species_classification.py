"""
StreetPaw.AI — Comprehensive Multi-Species Classification & Vision Pipeline Tests.
Validates:
1. Non-dog species (Cat, Cow, Pig, Horse) are accurately classified and NOT classified as Dog.
2. Dog breed and skin disease models execute ONLY IF species == 'Dog'.
3. For non-dogs, breed is None and disease is 'Not analyzed by dog disease model'.
4. Blank / non-animal images are classified as Neither / Plant and NEVER defaulted to Dog.
5. True dogs unlock breed classification and disease profiling as expected.
6. Animal Re-ID cosine similarity search functions properly.
"""

import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app, load_models

# Ensure models are loaded before tests run
load_models()
client = TestClient(app)

def get_asset_path(filename):
    return os.path.join(os.path.dirname(__file__), "fixtures", filename)

def test_cat_classification_locks_dog_models():
    """Cat images must be classified as Cat with dog breed and disease models locked."""
    path = get_asset_path("test_cat.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_cat.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert len(data["detections"]) > 0

    det = data["detections"][0]
    assert det["species"] == "Cat", f"Expected Cat, got {det['species']}"
    assert det["confidence"] > 50.0
    assert det["is_animal"] is True
    assert det["is_human"] is False

    # Dog-specific models MUST NOT run for Cat
    assert det["breed"] is None, f"Breed should be None for Cat, got {det['breed']}"
    assert det["breed_confidence"] == 0.0
    assert det["disease"] == "Not analyzed by dog disease model"
    assert det["disease_status"] == "not_applicable"

def test_dog_classification_runs_dog_models():
    """Dog images must be classified as Dog and run EfficientNet-B3 breed and disease classifiers."""
    path = get_asset_path("test_dog.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_dog.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert len(data["detections"]) > 0

    det = data["detections"][0]
    assert det["species"] == "Dog", f"Expected Dog, got {det['species']}"
    assert det["confidence"] > 70.0
    assert det["is_animal"] is True

    # Dog-specific models MUST run for Dog
    assert det["breed"] is not None and det["breed"] != "None"
    assert det["breed_confidence"] > 0.0
    assert det["disease"] is not None
    assert det["disease_status"] in ["normal", "disease_detected"]

def test_cow_classification_locks_dog_models():
    """Cow images must be classified as Cow (or Buffalo/Bull) and lock dog models."""
    path = get_asset_path("test_cow.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_cow.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True

    det = data["detections"][0]
    assert det["species"] in ["Cow", "Bull", "Buffalo"], f"Expected Cow/Bull/Buffalo, got {det['species']}"
    assert det["breed"] is None
    assert det["disease"] == "Not analyzed by dog disease model"
    assert det["disease_status"] == "not_applicable"

def test_pig_classification_locks_dog_models():
    """Pig images must be classified as Pig and lock dog models."""
    path = get_asset_path("test_pig.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_pig.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True

    det = data["detections"][0]
    assert det["species"] == "Pig", f"Expected Pig, got {det['species']}"
    assert det["breed"] is None
    assert det["disease"] == "Not analyzed by dog disease model"
    assert det["disease_status"] == "not_applicable"

def test_horse_classification_locks_dog_models():
    """Horse images must be classified as Horse and lock dog models."""
    path = get_asset_path("test_horse.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_horse.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True

    det = data["detections"][0]
    assert det["species"] in ["Horse", "Donkey"], f"Expected Horse/Donkey, got {det['species']}"
    assert det["breed"] is None
    assert det["disease"] == "Not analyzed by dog disease model"
    assert det["disease_status"] == "not_applicable"

def test_blank_non_animal_never_defaults_to_dog():
    """Blank or non-animal scenes must NOT be classified as Dog."""
    path = get_asset_path("test_blank.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_blank.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    det = data["detections"][0]
    assert det["species"] != "Dog", "Blank image must NEVER default to Dog!"
    assert det["species"] in ["Neither", "Unknown / Low Confidence"]
    assert det["is_animal"] is False

def test_plant_scene_detected_as_plant():
    """Plant/foliage scenes must be identified as Plant, not Dog."""
    path = get_asset_path("test_plant.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/detect", files={"file": ("upload_plant.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    det = data["detections"][0]
    assert det["species"] == "Plant"
    assert det["is_plant"] is True
    assert det["is_animal"] is False
    assert det["breed"] is None
    assert det["disease_status"] == "not_applicable"

def test_animal_reid_endpoint():
    """Re-ID cosine similarity search endpoint must function properly."""
    path = get_asset_path("test_dog.jpg")
    with open(path, "rb") as f:
        response = client.post("/api/animal-id", files={"file": ("dog_reid.jpg", f, "image/jpeg")})
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert "animal_id" in data
    assert "similarity" in data

if __name__ == "__main__":
    tests = [
        test_cat_classification_locks_dog_models,
        test_dog_classification_runs_dog_models,
        test_cow_classification_locks_dog_models,
        test_pig_classification_locks_dog_models,
        test_horse_classification_locks_dog_models,
        test_blank_non_animal_never_defaults_to_dog,
        test_plant_scene_detected_as_plant,
        test_animal_reid_endpoint,
    ]
    print("\n" + "="*60)
    print("RUNNING STREETPAW MULTI-SPECIES & VISION PIPELINE TESTS")
    print("="*60)
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            raise e
    print("="*60)
    print(f"ALL {passed}/{len(tests)} TESTS PASSED PERFECTLY!")
    print("="*60)
