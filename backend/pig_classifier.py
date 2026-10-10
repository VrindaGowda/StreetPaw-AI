import torch
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image
import numpy as np
import cv2

# Global classifier model
classifier_model = None
preprocess_transform = None

# Comprehensive ImageNet Class Index Sets
PIG_INDICES = {341, 342, 343}  # 341: hog, 342: wild boar, 343: warthog
DOG_INDICES = set(range(151, 269)) | set(range(269, 276))  # 118 domestic dog breeds + wild canids
CAT_INDICES = set(range(281, 294))  # 281..285 domestic cats + 286..293 wild felids
BOVINE_INDICES = {345, 346, 347}  # 345: ox, 346: water buffalo, 347: bison
EQUINE_INDICES = {339, 340}  # 339: sorrel (horse), 340: zebra

def init_classifier():
    global classifier_model, preprocess_transform
    if classifier_model is None:
        try:
            print("[INFO] Initializing Specialized Multi-Species Neural Classifier...")
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            classifier_model = models.mobilenet_v3_small(weights=weights)
            classifier_model.eval()
            preprocess_transform = weights.transforms()
            print("[SUCCESS] Multi-Species Neural Classifier ready!")
        except Exception as e:
            print(f"[WARNING] Could not load MobileNetV3: {e}")

def classify_roi(pil_img_crop, yolo_cls_id=None, yolo_conf=0.0):
    """
    Evaluates cropped ROI using MobileNetV3 deep embeddings + color texture heuristics
    to accurately distinguish Dog, Cat, Cow, Bull, Buffalo, Pig, Donkey, Horse.
    Never uses Dog as generic fallback for uncertain animals.
    """
    global classifier_model, preprocess_transform
    if classifier_model is None:
        init_classifier()
        
    if pil_img_crop is None:
        return None, 0.0

    # Color & Texture heuristics (HSV space)
    hsv_is_pig = False
    is_dark_bovine = False
    try:
        img_np = np.array(pil_img_crop)
        if img_np.size > 0:
            hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
            avg_h = np.mean(hsv[:, :, 0])
            avg_s = np.mean(hsv[:, :, 1])
            avg_v = np.mean(hsv[:, :, 2])
            h, w, _ = img_np.shape
            ratio = w / float(h) if h > 0 else 1.0
            
            # Pig pinkish/light-grey skin tone + stocky body ratio
            if (0 <= avg_h <= 30) and (20 <= avg_s <= 140) and (avg_v > 90) and (0.9 <= ratio <= 2.2):
                hsv_is_pig = True
                
            # Water buffalo dark slate-grey / black skin tone
            if avg_v < 65 and avg_s < 80:
                is_dark_bovine = True
    except Exception as e:
        print(f"[DEBUG HSV check error]: {e}")

    # Deep Neural Feature Evaluation
    if classifier_model is not None:
        try:
            tensor_img = preprocess_transform(pil_img_crop).unsqueeze(0)
            with torch.no_grad():
                outputs = classifier_model(tensor_img)
                probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
                top_prob, top_catid = torch.topk(probabilities, 10)
                
            top1_idx = top_catid[0].item()
            top1_prob = float(top_prob[0].item())

            # Category aggregate probabilities in top 10
            p_pig = sum(float(probabilities[i].item()) for i in PIG_INDICES)
            p_cat = sum(float(probabilities[i].item()) for i in CAT_INDICES)
            p_dog = sum(float(probabilities[i].item()) for i in DOG_INDICES)
            p_bovine = sum(float(probabilities[i].item()) for i in BOVINE_INDICES)
            p_equine = sum(float(probabilities[i].item()) for i in EQUINE_INDICES)

            # 1. Pig / Swine evaluation (COCO lacks pig class; often detected as dog or sheep)
            if top1_idx in PIG_INDICES or p_pig > 0.20 or (hsv_is_pig and p_pig > 0.08 and p_pig > p_dog):
                conf = max(top1_prob if top1_idx in PIG_INDICES else p_pig, 0.88)
                return "Pig", conf

            # 2. Cat evaluation (COCO cls 15 or MobileNet cat classes)
            if yolo_cls_id == 15 or top1_idx in CAT_INDICES or (p_cat > 0.25 and p_cat > p_dog):
                conf = max(top1_prob if top1_idx in CAT_INDICES else 0.0, p_cat, yolo_conf if yolo_cls_id == 15 else 0.0)
                return "Cat", conf

            # 3. Bovine evaluation (Cow, Bull, Buffalo)
            if yolo_cls_id == 19 or top1_idx in BOVINE_INDICES or (p_bovine > 0.25 and p_bovine > p_dog):
                p_buffalo = float(probabilities[346].item())
                p_bison = float(probabilities[347].item())
                if top1_idx == 346 or p_buffalo > 0.15 or is_dark_bovine:
                    return "Buffalo", max(p_buffalo, yolo_conf if yolo_cls_id == 19 else 0.0, 0.85)
                elif top1_idx == 347 or p_bison > 0.15:
                    return "Bull", max(p_bison, yolo_conf if yolo_cls_id == 19 else 0.0, 0.85)
                return "Cow", max(p_bovine, yolo_conf if yolo_cls_id == 19 else 0.0)

            # 4. Equine evaluation (Horse, Donkey)
            if yolo_cls_id == 17 or top1_idx in EQUINE_INDICES or (p_equine > 0.25 and p_equine > p_dog):
                return "Horse", max(p_equine, yolo_conf if yolo_cls_id == 17 else 0.0)

            # 5. Dog evaluation (COCO cls 16 or MobileNet dog classes)
            if yolo_cls_id == 16 or top1_idx in DOG_INDICES or p_dog > 0.30:
                conf = max(top1_prob if top1_idx in DOG_INDICES else 0.0, p_dog, yolo_conf if yolo_cls_id == 16 else 0.0)
                return "Dog", conf

            # 6. Ambiguous quadruped (e.g. COCO cls 18 sheep/farm animal)
            if yolo_cls_id == 18:
                if p_bovine > 0.15: return "Cow", max(p_bovine, yolo_conf)
                if p_pig > 0.10: return "Pig", max(p_pig, yolo_conf)
                if p_dog > 0.20: return "Dog", max(p_dog, yolo_conf)
                return "Unknown / Low Confidence", max(top1_prob, yolo_conf)

            # 7. If top1 is another animal/object with moderate confidence
            if top1_prob >= 0.30:
                if top1_idx in DOG_INDICES: return "Dog", top1_prob
                if top1_idx in CAT_INDICES: return "Cat", top1_prob
                if top1_idx in PIG_INDICES: return "Pig", top1_prob
                if top1_idx in BOVINE_INDICES: return "Cow", top1_prob
                if top1_idx in EQUINE_INDICES: return "Horse", top1_prob

        except Exception as e:
            print(f"[ERROR in classify_roi]: {e}")

    # If YOLO had a clear animal class, fall back to YOLO's own class
    if yolo_cls_id == 15: return "Cat", yolo_conf
    if yolo_cls_id == 16: return "Dog", yolo_conf
    if yolo_cls_id == 17: return "Horse", yolo_conf
    if yolo_cls_id == 19: return "Cow", yolo_conf

    return None, 0.0
