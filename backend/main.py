import io
import os
import base64
import time
import random
from PIL import Image
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pig_classifier import init_classifier, classify_roi
from animal_reid import AnimalReID
from breed_classifier import init_breed_classifier, classify_breed, is_model_ready
from disease_classifier import init_disease_classifier, classify_disease, is_disease_model_ready

from db.database import engine, Base
from routers.ai_router import ai_router, set_ai_models
from routers.rescues_router import rescues_router, complaints_router
from routers.dogs_router import dogs_router
from routers.auth_router import auth_router
from routers.admin_router import admin_router
from routers.users_router import users_router
from routers.contacts_router import contacts_router
from routers.chat_router import chat_router
from routers.lost_found_router import lost_found_router
from routers.analytics_router import analytics_router
from routers.exports_router import exports_router

# Create SQLAlchemy Database Tables on Startup
Base.metadata.create_all(bind=engine)

# Initialize FastAPI App
app = FastAPI(
    title="StreetPaw.AI Multi-Animal Vision & Rescue Engine",
    description="Collaborative Multi-Agent Platform for Stray Animal Welfare",
    version="6.0.0"
)

# Enable CORS locked to Citizen App (:5173) and NGO Portal (:5174)
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular API Routers
app.include_router(ai_router)
app.include_router(rescues_router)
app.include_router(complaints_router)
app.include_router(dogs_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(users_router)
app.include_router(contacts_router)
app.include_router(chat_router)
app.include_router(lost_found_router)
app.include_router(analytics_router)
app.include_router(exports_router)




# Global YOLO model holder
yolo_model = None
reid_model = None

# Known COCO Plant / Non-Animal Object classes
NON_ANIMAL_COCO_CLASSES = {
    58: "Plant / Foliage",
    59: "Bed / Furniture",
    60: "Dining Table",
    61: "Toilet",
    62: "TV / Screen",
    63: "Laptop",
    64: "Mouse",
    65: "Remote",
    66: "Keyboard",
    67: "Cell Phone",
    73: "Book",
    74: "Clock",
    75: "Vase",
    76: "Scissors",
    77: "Teddy Bear",
    78: "Hair Drier",
    79: "Toothbrush"
}

SUPPORTED_SPECIES = ["Dog", "Cat", "Cow", "Bull", "Buffalo", "Pig", "Donkey", "Horse", "Human", "Plant", "Neither"]

def load_models():
    global yolo_model, reid_model
    if yolo_model is None:
        try:
            from ultralytics import YOLO
            print("[INFO] Loading YOLOv8 Vision Model...")
            yolo_model = YOLO("yolov8n.pt")
            print("[SUCCESS] YOLOv8 model loaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to load YOLOv8 model: {e}")
            yolo_model = None
            
    init_classifier()
    if reid_model is None:
        try:
            print("[INFO] Loading Animal Re-ID model...")
            reid_model = AnimalReID()
            print("[SUCCESS] Animal Re-ID model loaded successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to load Animal Re-ID model: {e}")
            reid_model = None

    init_breed_classifier()
    init_disease_classifier()
    set_ai_models(yolo_model, reid_model)

@app.on_event("startup")
async def startup_event():
    load_models()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "StreetPaw.AI Strict Vision Engine",
        "supported_animals": SUPPORTED_SPECIES,
        "yolo_active": yolo_model is not None,
        "breed_model_ready": is_model_ready(),
        "disease_model_ready": is_disease_model_ready()
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "yolo_active": yolo_model is not None,
        "breed_model_ready": is_model_ready(),
        "disease_model_ready": is_disease_model_ready()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

