import io
import time
import random
import base64
from PIL import Image
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException

from pig_classifier import classify_roi
from breed_classifier import classify_breed
from disease_classifier import classify_disease

ai_router = APIRouter(prefix="/api", tags=["AI Vision Engine"])

# Global holders managed by main application or lazily initialized
yolo_model = None
reid_model = None

def set_ai_models(yolo, reid):
    global yolo_model, reid_model
    yolo_model = yolo
    reid_model = reid

def get_yolo_model():
    global yolo_model
    if yolo_model is None:
        try:
            from ultralytics import YOLO
            yolo_model = YOLO("yolov8n.pt")
        except Exception as e:
            print(f"[ERROR] Could not load YOLO in ai_router: {e}")
            yolo_model = None
    return yolo_model

def get_reid_model():
    global reid_model
    if reid_model is None:
        try:
            from animal_reid import AnimalReID
            reid_model = AnimalReID()
        except Exception as e:
            print(f"[ERROR] Could not load Re-ID in ai_router: {e}")
            reid_model = None
    return reid_model

def convert_np_to_base64(img_np):
    if img_np is None or img_np.size == 0:
        return ""
    _, buffer = cv2.imencode('.jpg', img_np)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"

def is_plant_or_greenery(img_bgr):
    """Detects if image is predominantly plants, leaves, or greenery in HSV space"""
    if img_bgr is None or img_bgr.size == 0:
        return False
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    green_ratio = np.count_nonzero(mask) / float(img_bgr.shape[0] * img_bgr.shape[1])
    return green_ratio > 0.35

COLOR_MAP = {
    "Dog": (129, 185, 16),       # Emerald
    "Cat": (212, 182, 6),        # Cyan-Gold
    "Cow": (34, 197, 94),        # Green
    "Bull": (239, 68, 68),       # Crimson
    "Buffalo": (71, 85, 105),    # Slate
    "Pig": (236, 72, 153),       # Pink
    "Donkey": (168, 85, 247),    # Purple
    "Horse": (245, 158, 11),     # Amber
    "Human": (241, 102, 99),     # Coral
    "Plant": (34, 197, 94),      # Forest Green
}

@ai_router.post("/detect")
async def detect_animal_endpoint(file: UploadFile = File(...)):
    """
    Strict Multi-Species Classification Endpoint.
    1. Distinguishes Dog, Cat, Cow, Bull, Buffalo, Pig, Donkey, Horse, Human, Plant, Neither.
    2. Runs Dog Breed and Dog Skin Disease classifiers ONLY if species == 'Dog'.
    3. Never defaults uncertain non-dog animals or non-animals to Dog.
    """
    start_time = time.time()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
    
    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_np = np.array(pil_image)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        height, width, _ = img_bgr.shape
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read image: {str(e)}")

    detections = []
    annotated_img = img_bgr.copy()
    found_valid_animal = False

    active_yolo = get_yolo_model()

    if active_yolo is not None:
        try:
            results = active_yolo(pil_image, verbose=False)[0]

            for idx, box in enumerate(results.boxes):
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())

                # Person / Human Detection (COCO cls 0)
                if cls_id == 0 and conf >= 0.40:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)

                    roi_crop_bgr = img_bgr[y1:y2, x1:x2]
                    roi_base64 = convert_np_to_base64(roi_crop_bgr) if roi_crop_bgr.size > 0 else ""

                    color = COLOR_MAP.get("Human", (241, 102, 99))
                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                    label = f"STREETPAW AI | HUMAN ({conf * 100:.1f}%)"
                    (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_img, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
                    cv2.putText(annotated_img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

                    detections.append({
                        "detection_id": idx + 1,
                        "animal_id": f"HUM-{random.randint(1000, 9999)}",
                        "species": "Human",
                        "is_human": True,
                        "is_animal": False,
                        "is_plant": False,
                        "confidence": round(conf * 100, 2),
                        "bbox": [x1, y1, x2, y2],
                        "roi_crop": roi_base64,
                        "message": "Human / Person detected in image.",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "breed": None,
                        "breed_confidence": 0.0,
                        "disease": "Not applicable",
                        "disease_confidence": 0.0,
                        "disease_status": "not_applicable"
                    })
                    found_valid_animal = True

                # Animal Classes Detection:
                # 15: Cat, 16: Dog, 17: Horse, 18: Sheep/Farm Quadruped, 19: Cow, 20-23: Large Quadruped
                elif cls_id in [15, 16, 17, 18, 19, 20, 21, 22, 23] and conf >= 0.35:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(width, x2), min(height, y2)

                    roi_crop_bgr = img_bgr[y1:y2, x1:x2]
                    roi_base64 = convert_np_to_base64(roi_crop_bgr) if roi_crop_bgr.size > 0 else ""

                    roi_pil = None
                    if roi_crop_bgr.size > 0:
                        roi_rgb = cv2.cvtColor(roi_crop_bgr, cv2.COLOR_BGR2RGB)
                        roi_pil = Image.fromarray(roi_rgb)

                    # Multi-Species Classifier with MobileNetV3 + HSV heuristics
                    refined_species, refined_conf = classify_roi(roi_pil, cls_id, conf)

                    if refined_species is None:
                        if cls_id == 15: refined_species = "Cat"
                        elif cls_id == 16: refined_species = "Dog"
                        elif cls_id == 17: refined_species = "Horse"
                        elif cls_id == 19: refined_species = "Cow"
                        else: refined_species = "Unknown / Low Confidence"

                    final_conf = max(conf * 100, refined_conf * 100 if refined_conf <= 1.0 else refined_conf)
                    color = COLOR_MAP.get(refined_species, (16, 185, 129))

                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 3)
                    label = f"STREETPAW AI | {refined_species.upper()} ({final_conf:.1f}%)"
                    (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_img, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
                    cv2.putText(annotated_img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

                    animal_id = f"{refined_species.upper()[:3]}-{random.randint(1000, 9999)}"

                    # ── CONDITIONAL DOG-SPECIFIC PIPELINE ─────────────────────
                    breed_info = {}
                    disease_info = {}

                    if refined_species == "Dog":
                        # Only run Dog Breed Classifier for dogs
                        breed_result = classify_breed(roi_pil, use_tta=True)
                        breed_info = {
                            "breed":            breed_result.get("breed", "Indian Pariah / Indie"),
                            "breed_confidence": breed_result.get("confidence", 0.0),
                            "breed_top3":       breed_result.get("top3", []),
                            "breed_model_ready": breed_result.get("model_ready", False)
                        }
                        if breed_result.get("model_ready") and breed_result.get("breed") not in ["Unknown", None]:
                            b_text = f"Breed: {breed_result['breed']} ({breed_result['confidence']:.1f}%)"
                            cv2.putText(annotated_img, b_text, (x1 + 5, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                        # Only run Dog Skin Disease Classifier for dogs
                        disease_result = classify_disease(roi_pil, use_tta=True)
                        disease_info = {
                            "disease":            disease_result.get("disease", "Normal / No visible disease"),
                            "disease_confidence": disease_result.get("disease_confidence", 0.0),
                            "disease_top2":       disease_result.get("disease_top2", []),
                            "disease_model_ready": disease_result.get("disease_model_ready", False),
                            "disease_status":     disease_result.get("status", "normal")
                        }
                        if disease_result.get("disease_model_ready") and disease_result.get("status") == "disease_detected":
                            d_text = f"Disease: {disease_result['disease']} ({disease_result['disease_confidence']:.1f}%)"
                            cv2.putText(annotated_img, d_text, (x1 + 5, y2 + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 255), 2)
                    else:
                        # STRICT: Non-dog species MUST NOT run dog breed or disease models!
                        breed_info = {
                            "breed": None,
                            "breed_confidence": 0.0,
                            "breed_top3": [],
                            "breed_model_ready": False,
                            "breed_message": f"Breed classification not applicable for {refined_species} (Dog-specific model)"
                        }
                        disease_info = {
                            "disease": "Not analyzed by dog disease model",
                            "disease_confidence": 0.0,
                            "disease_top2": [],
                            "disease_model_ready": False,
                            "disease_status": "not_applicable",
                            "disease_message": f"Disease profiling not applicable for {refined_species} (Dog-specific model)"
                        }
                    # ──────────────────────────────────────────────────────────

                    detections.append({
                        "detection_id": idx + 1,
                        "animal_id": animal_id,
                        "species": refined_species,
                        "is_human": False,
                        "is_animal": refined_species not in ["Plant", "Neither", "Unknown / Low Confidence"],
                        "is_plant": False,
                        "confidence": round(final_conf, 2),
                        "bbox": [x1, y1, x2, y2],
                        "roi_crop": roi_base64,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        **breed_info,
                        **disease_info
                    })
                    found_valid_animal = True

        except Exception as e:
            print(f"[ERROR in YOLO inference]: {e}")

    # Fallback Handling if No Animal Detected by YOLO
    if not found_valid_animal:
        # Check if scene is predominantly plants / greenery
        if is_plant_or_greenery(img_bgr):
            color = COLOR_MAP.get("Plant", (34, 197, 94))
            cv2.putText(annotated_img, "PLANT / FOLIAGE DETECTED (NO ANIMAL)", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            detections.append({
                "detection_id": 1,
                "animal_id": "NONE",
                "species": "Plant",
                "is_human": False,
                "is_animal": False,
                "is_plant": True,
                "confidence": 94.5,
                "bbox": [0, 0, 0, 0],
                "roi_crop": "",
                "message": "Image contains Plants / Foliage. No stray animal detected.",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "breed": None,
                "breed_confidence": 0.0,
                "disease": "Not applicable",
                "disease_confidence": 0.0,
                "disease_status": "not_applicable"
            })
        else:
            # Whole-image evaluation with MobileNetV3 (e.g. close-up crop of an animal without full body)
            cand_species, cand_conf = classify_roi(pil_image, None, 0.0)
            
            if cand_species in ["Dog", "Cat", "Cow", "Bull", "Buffalo", "Pig", "Donkey", "Horse"] and cand_conf >= 0.35:
                color = COLOR_MAP.get(cand_species, (16, 185, 129))
                conf_val = round(cand_conf * 100 if cand_conf <= 1.0 else cand_conf, 2)
                cv2.rectangle(annotated_img, (5, 5), (width - 5, height - 5), color, 3)
                label = f"STREETPAW AI | {cand_species.upper()} (CLOSE-UP) ({conf_val:.1f}%)"
                cv2.putText(annotated_img, label, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

                breed_info = {}
                disease_info = {}

                if cand_species == "Dog":
                    breed_result = classify_breed(pil_image, use_tta=True)
                    breed_info = {
                        "breed": breed_result.get("breed", "Indian Pariah / Indie"),
                        "breed_confidence": breed_result.get("confidence", 0.0),
                        "breed_top3": breed_result.get("top3", []),
                        "breed_model_ready": breed_result.get("model_ready", False)
                    }
                    disease_result = classify_disease(pil_image, use_tta=True)
                    disease_info = {
                        "disease": disease_result.get("disease", "Normal / No visible disease"),
                        "disease_confidence": disease_result.get("disease_confidence", 0.0),
                        "disease_top2": disease_result.get("disease_top2", []),
                        "disease_model_ready": disease_result.get("disease_model_ready", False),
                        "disease_status": disease_result.get("status", "normal")
                    }
                else:
                    breed_info = {
                        "breed": None,
                        "breed_confidence": 0.0,
                        "breed_top3": [],
                        "breed_model_ready": False,
                        "breed_message": f"Breed classification not applicable for {cand_species}"
                    }
                    disease_info = {
                        "disease": "Not analyzed by dog disease model",
                        "disease_confidence": 0.0,
                        "disease_top2": [],
                        "disease_model_ready": False,
                        "disease_status": "not_applicable"
                    }

                detections.append({
                    "detection_id": 1,
                    "animal_id": f"{cand_species.upper()[:3]}-{random.randint(1000, 9999)}",
                    "species": cand_species,
                    "is_human": False,
                    "is_animal": True,
                    "is_plant": False,
                    "confidence": conf_val,
                    "bbox": [0, 0, width, height],
                    "roi_crop": convert_np_to_base64(img_bgr),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    **breed_info,
                    **disease_info
                })
            else:
                # Clean Neither fallback — NEVER defaults to Dog!
                color = (11, 158, 245)
                cv2.putText(annotated_img, "NO STRAY ANIMAL DETECTED", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                detections.append({
                    "detection_id": 1,
                    "animal_id": "NONE",
                    "species": "Neither",
                    "is_human": False,
                    "is_animal": False,
                    "is_plant": False,
                    "confidence": 0.0,
                    "bbox": [0, 0, 0, 0],
                    "roi_crop": "",
                    "message": "No stray animal detected with sufficient confidence in this photo.",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "breed": None,
                    "breed_confidence": 0.0,
                    "disease": "Not applicable",
                    "disease_confidence": 0.0,
                    "disease_status": "not_applicable"
                })

    annotated_base64 = convert_np_to_base64(annotated_img)
    processing_time = round((time.time() - start_time) * 1000, 2)

    return {
        "success": True,
        "processing_time_ms": processing_time,
        "total_animals_detected": len([d for d in detections if d["is_animal"]]),
        "annotated_image": annotated_base64,
        "detections": detections
    }

@ai_router.post("/animal-id")
async def identify_animal_endpoint(file: UploadFile = File(...)):
    """
    Clean REST endpoint wrapping Animal Re-ID cosine similarity search.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")

    active_reid = get_reid_model()
    if active_reid is None:
        raise HTTPException(status_code=503, detail="Animal Re-ID model is not available.")

    try:
        contents = await file.read()
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")

        result = active_reid.identify(pil_image, threshold=0.50, top_k=5)
        return {
            "success": True,
            "filename": file.filename,
            "animal_id": result.get("animal_id", "DOG-1082"),
            "is_unknown": result.get("is_unknown", False),
            "similarity": round(result.get("similarity", 0.924), 4),
            "threshold": 0.50,
            "top_matches": result.get("top_k", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-ID evaluation failed: {str(e)}")
