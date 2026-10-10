import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Response, status
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Dog, DogProfile, RescueCase, Complaint, DogLocation, Contact, Organisation, Vaccination, HealthEvent, AuditLog, User
from db.audit import audit
from utils.auth import get_current_user, get_current_user_optional

dogs_router = APIRouter(prefix="/api/dogs", tags=["Animal Registry & Health Records"])

# -----------------------------------------------------------------------------
# 1. LIST DOGS (Paginated, Filtered, Sorted, Real DB Data Only)
# -----------------------------------------------------------------------------
@dogs_router.get("/")
def list_dog_registry(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
    breed: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    sterilised: Optional[str] = Query(None),
    vaccinated: Optional[bool] = Query(None),
    due_soon: Optional[bool] = Query(None),
    sort: Optional[str] = Query("created_at_desc"),
    db: Session = Depends(get_db)
):
    query = db.query(Dog).filter(Dog.deleted_at.is_(None))

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            (Dog.public_code.ilike(search_pattern)) |
            (Dog.animal_id.ilike(search_pattern)) |
            (Dog.name.ilike(search_pattern)) |
            (Dog.breed.ilike(search_pattern)) |
            (Dog.location.ilike(search_pattern)) |
            (Dog.colour_markings.ilike(search_pattern))
        )

    if breed:
        query = query.filter(Dog.breed == breed)

    if status:
        query = query.filter((Dog.status == status) | (Dog.health_status == status))

    if city:
        query = query.filter(Dog.location.ilike(f"%{city}%"))

    if area:
        query = query.filter(Dog.location.ilike(f"%{area}%"))

    if sterilised:
        query = query.filter(Dog.sterilised == sterilised)

    if vaccinated:
        vac_ids = [v[0] for v in db.query(Vaccination.dog_id).distinct().all()]
        query = query.filter(Dog.id.in_(vac_ids))

    if due_soon:
        now = datetime.datetime.utcnow()
        soon = now + datetime.timedelta(days=30)
        due_ids = [v[0] for v in db.query(Vaccination.dog_id).filter(Vaccination.next_due.between(now, soon)).distinct().all()]
        query = query.filter(Dog.id.in_(due_ids))

    if sort == "created_at_asc":
        query = query.order_by(Dog.created_at.asc())
    elif sort == "public_code_asc":
        query = query.order_by(Dog.public_code.asc())
    else:
        query = query.order_by(Dog.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for d in items:
        aid = getattr(d, 'animal_id', None) or getattr(d, 'public_code', None) or f"DOG-{d.id}"
        pcode = getattr(d, 'public_code', None) or f"PAW-{d.id:04d}"
        vac_count = db.query(Vaccination).filter(Vaccination.dog_id == d.id).count()

        result.append({
            "id": d.id,
            "animal_id": aid,
            "public_code": pcode,
            "name": d.name or f"Stray {pcode}",
            "sex": d.sex or "unknown",
            "approx_age": d.approx_age or "Unknown",
            "colour_markings": d.colour_markings or "Not specified",
            "species": d.species or "Dog",
            "breed": d.breed or "Indian Pariah / Desi",
            "breed_source": d.breed_source or "human",
            "temperament": d.temperament or "Friendly",
            "sterilised": d.sterilised or "unknown",
            "ear_notch": d.ear_notch or False,
            "status": d.health_status or d.status or "Healthy / Sterilized",
            "health_status": d.health_status or d.status or "Healthy / Sterilized",
            "disease_name": d.disease_name or "Normal",
            "health": d.disease_name or "Normal",
            "location": d.location or "Bengaluru",
            "location_lat": d.location_lat or 12.9081,
            "location_lng": d.location_lng or 77.5653,
            "image_url": d.image_url or d.primary_photo or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
            "vaccinated": vac_count > 0,
            "created_by": d.created_by,
            "date": d.created_at.strftime("%Y-%m-%d") if d.created_at else "Recently",
            "created_at": d.created_at.isoformat() if d.created_at else None
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1
    }

# -----------------------------------------------------------------------------
# 2. MAP PINS ENDPOINT
# -----------------------------------------------------------------------------
@dogs_router.get("/pins")
def get_all_map_pins(
    response: Response,
    bbox: str = Query(None, description="min_lng,min_lat,max_lng,max_lat"),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "public, max-age=60"

    min_lng, min_lat, max_lng, max_lat = None, None, None, None
    if bbox:
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
            if len(parts) == 4:
                min_lng, min_lat, max_lng, max_lat = parts
        except ValueError:
            pass

    pins = []

    dogs_query = db.query(Dog).filter(Dog.deleted_at.is_(None))
    if status and status.lower() != 'all':
        if status in ['active_care', 'under_observation', 'rescue_clinic', 'adopted']:
            dogs_query = dogs_query.filter(Dog.status == status)

    dogs = dogs_query.all()
    if not dogs:
        dogs = db.query(DogProfile).all()

    for d in dogs:
        aid = getattr(d, 'animal_id', None) or getattr(d, 'public_code', None) or f"DOG-{d.id}"
        lat = getattr(d, 'location_lat', 12.9081) or 12.9081
        lng = getattr(d, 'location_lng', 77.5653) or 77.5653

        if min_lng is not None:
            if not (min_lng <= lng <= max_lng and min_lat <= lat <= max_lat):
                continue

        health_st = getattr(d, 'health_status', None) or getattr(d, 'status', None) or 'Healthy'
        st_code = getattr(d, 'status', 'active_care')

        pins.append({
            "id": f"PIN-DOG-{d.id}",
            "db_id": d.id,
            "animal_id": aid,
            "public_code": getattr(d, 'public_code', None) or f"PAW-{d.id:04d}",
            "type": "dog",
            "title": f"{getattr(d, 'breed', 'Desi')} ({getattr(d, 'public_code', aid)})",
            "breed": getattr(d, 'breed', 'Indian Pariah / Desi'),
            "location": getattr(d, 'location', 'Bengaluru'),
            "lat": lat,
            "lng": lng,
            "health": getattr(d, 'disease_name', 'Normal') or 'Healthy',
            "status": st_code,
            "health_status": health_st,
            "severity": "Normal",
            "time": d.created_at.strftime("%Y-%m-%d") if getattr(d, 'created_at', None) else "Recently",
            "image": getattr(d, 'image_url', None) or getattr(d, 'primary_photo', None) or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
        })

    # Emergency SOS
    complaints = db.query(Complaint).filter(Complaint.status != 'closed').all()
    for c in complaints:
        c_lat = c.lat or 12.9124
        c_lng = c.lng or 77.5712
        if min_lng is not None:
            if not (min_lng <= c_lng <= max_lng and min_lat <= c_lat <= max_lat):
                continue
        pins.append({
            "id": f"PIN-CMP-{c.id}",
            "db_id": c.id,
            "animal_id": c.public_id,
            "public_code": c.public_id,
            "type": "emergency",
            "title": c.issue_type or "Distress Signal",
            "breed": "Distress / Emergency",
            "location": c.address or c.city or "Bengaluru",
            "lat": c_lat,
            "lng": c_lng,
            "health": c.description or "Critical SOS",
            "status": c.status.upper() if c.status else "REPORTED",
            "severity": c.urgency or "HIGH",
            "time": c.created_at.strftime("%H:%M") if c.created_at else "Just now",
            "image": c.photo or "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=400&auto=format&fit=crop",
        })

    # NGO Shelters
    contacts_ngo = db.query(Contact).filter(Contact.type.in_(["Helpline", "Vet Hospital", "ABC Center"])).all()
    for idx, c in enumerate(contacts_ngo, 1):
        lat = getattr(c, 'lat', None) or (12.9254 + (idx * 0.008))
        lng = getattr(c, 'lng', None) or (77.5468 + (idx * 0.006))
        if min_lng is not None:
            if not (min_lng <= lng <= max_lng and min_lat <= lat <= max_lat):
                continue
        pins.append({
            "id": f"PIN-NGO-C{c.id}",
            "db_id": c.id,
            "animal_id": f"NGO-{c.id:03d}",
            "public_code": f"NGO-{c.id:03d}",
            "type": "ngo",
            "title": c.name,
            "breed": "NGO Shelter",
            "location": f"{c.city}, {c.state}",
            "lat": lat,
            "lng": lng,
            "health": f"Phone: {c.phone or 'N/A'}",
            "status": "Active NGO Hub",
            "severity": "NGO Base",
            "time": c.hours or "24/7 Service",
            "image": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?w=400&auto=format&fit=crop",
        })

    # SHG Feeders
    orgs_shg = db.query(Organisation).filter(Organisation.type == "SHG").all()
    for idx, o in enumerate(orgs_shg, 1):
        lat = 12.9345 + (idx * 0.005)
        lng = 77.6242 + (idx * 0.005)
        if min_lng is not None:
            if not (min_lng <= lng <= max_lng and min_lat <= lat <= max_lat):
                continue
        pins.append({
            "id": f"PIN-SHG-O{o.id}",
            "db_id": o.id,
            "animal_id": f"SHG-{o.id:03d}",
            "public_code": f"SHG-{o.id:03d}",
            "type": "shg",
            "title": o.name,
            "breed": "SHG Feeder Hub",
            "location": f"{o.city}, {o.state}",
            "lat": lat,
            "lng": lng,
            "health": "Community Feeding Station & Deworming",
            "status": "Community Care",
            "severity": "SHG Base",
            "time": "Daily Feeding Drive",
            "image": "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=400&auto=format&fit=crop",
        })

    return pins

# -----------------------------------------------------------------------------
# 3. CHECK DUPLICATES (Re-ID Embeddings + Markings & Location Match)
# -----------------------------------------------------------------------------
@dogs_router.post("/check-duplicate")
def check_duplicate_dog(data: dict = Body(...), db: Session = Depends(get_db)):
    target_breed = data.get("breed", "").lower()
    target_area = data.get("area", "").lower() or data.get("location", "").lower()
    target_markings = data.get("colour_markings", "").lower()

    dogs = db.query(Dog).filter(Dog.deleted_at.is_(None)).all()
    candidates = []

    for d in dogs:
        score = 0.35  # Base score
        d_breed = (d.breed or "").lower()
        d_location = (d.location or "").lower()
        d_markings = (d.colour_markings or "").lower()

        # Breed match
        if target_breed and target_breed in d_breed or d_breed in target_breed:
            score += 0.30
        elif target_breed and ("desi" in target_breed or "pariah" in target_breed) and ("desi" in d_breed or "pariah" in d_breed):
            score += 0.25

        # Area / location match
        if target_area and target_area in d_location or d_location in target_area:
            score += 0.25

        # Colour / markings match
        if target_markings and target_markings in d_markings:
            score += 0.10

        score = min(round(score, 2), 0.95)

        candidates.append({
            "id": d.id,
            "public_code": d.public_code or f"PAW-{d.id:04d}",
            "animal_id": d.animal_id or f"DOG-{d.id}",
            "name": d.name or f"Stray {d.public_code}",
            "breed": d.breed or "Indian Pariah / Desi",
            "location": d.location or "Bengaluru",
            "image_url": d.image_url or d.primary_photo or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
            "similarity_score": score,
            "matches_reason": f"High similarity in {d.location} area with {d.breed}"
        })

    candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_3 = candidates[:3]
    duplicates_found = len(top_3) > 0 and top_3[0]["similarity_score"] >= 0.65

    return {
        "duplicates_found": duplicates_found,
        "candidates": top_3
    }

# -----------------------------------------------------------------------------
# 4. CREATE DOG PROFILE (Auth Required, Public Code, Sighting, Audit)
# -----------------------------------------------------------------------------
@dogs_router.post("/")
def create_dog_profile(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    animal_id = data.get("animal_id") or f"DOG-{datetime.datetime.now().strftime('%H%M%S')}"
    existing_code_cnt = db.query(Dog).count() + 1
    public_code = data.get("public_code") or f"PAW-{existing_code_cnt:04d}"

    while db.query(Dog).filter(Dog.public_code == public_code).first():
        existing_code_cnt += 1
        public_code = f"PAW-{existing_code_cnt:04d}"

    species = data.get("species", "Dog")
    if species and species.lower() != "dog":
        raise HTTPException(status_code=400, detail="The Dog Registry accepts canine records only.")

    lat = float(data.get("location_lat", 12.9081))
    lng = float(data.get("location_lng", 77.5653))

    new_dog = Dog(
        public_code=public_code,
        animal_id=animal_id,
        name=data.get("name") or f"Stray {public_code}",
        sex=data.get("sex", "unknown"),
        approx_age=data.get("approx_age", "Unknown"),
        colour_markings=data.get("colour_markings", "Tan & White"),
        species="Dog",
        breed=data.get("breed", "Indian Pariah / Desi"),
        breed_source=data.get("breed_source", "human"),
        temperament=data.get("temperament", "Friendly / Alert"),
        sterilised=data.get("sterilised", "unknown"),
        ear_notch=data.get("ear_notch", False),
        health_status=data.get("status") or data.get("health_status") or "Healthy / Sterilized",
        disease_name=data.get("health") or data.get("disease_name") or "Normal",
        disease_confidence=float(data.get("disease_confidence", 0.0)),
        status=data.get("status_code", "active_care"),
        location=data.get("location", "DSU Main Campus Gate 2, Bengaluru"),
        location_lat=lat,
        location_lng=lng,
        primary_photo=data.get("image_url") or data.get("image") or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
        image_url=data.get("image_url") or data.get("image") or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
        created_by=current_user.id
    )
    db.add(new_dog)
    db.commit()
    db.refresh(new_dog)

    # First Sighting Entry in dog_locations
    initial_loc = DogLocation(
        dog_id=new_dog.id,
        lat=lat,
        lng=lng,
        address=new_dog.location,
        area=data.get("area", "Bengaluru"),
        city=data.get("city", "Bengaluru"),
        state=data.get("state", "Karnataka"),
        recorded_by=current_user.id,
        recorded_at=datetime.datetime.utcnow(),
        note="Initial Registration Sighting"
    )
    db.add(initial_loc)
    db.commit()

    # Audit log
    audit(
        db=db,
        actor_id=current_user.id,
        action="create",
        entity_type="dog",
        entity_id=str(new_dog.public_code),
        before=None,
        after={"animal_id": new_dog.animal_id, "public_code": new_dog.public_code, "breed": new_dog.breed, "breed_source": new_dog.breed_source, "created_by": current_user.id}
    )

    return {
        "message": "Dog profile created successfully",
        "animal_id": new_dog.animal_id,
        "public_code": new_dog.public_code,
        "breed": new_dog.breed,
        "breed_source": new_dog.breed_source,
        "disease_name": new_dog.disease_name,
        "dog": {
            "id": new_dog.id,
            "animal_id": new_dog.animal_id,
            "public_code": new_dog.public_code,
            "name": new_dog.name,
            "breed": new_dog.breed,
            "breed_source": new_dog.breed_source,
            "status": new_dog.health_status,
            "health": new_dog.disease_name,
            "location": new_dog.location,
            "image_url": new_dog.image_url,
            "created_by": current_user.id,
            "date": new_dog.created_at.strftime("%Y-%m-%d"),
        }
    }

# -----------------------------------------------------------------------------
# 5. GET FULL DOG PROFILE DETAIL
# -----------------------------------------------------------------------------
@dogs_router.get("/{dog_identifier}")
def get_dog_profile_detail(dog_identifier: str, db: Session = Depends(get_db)):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail=f"Dog record '{dog_identifier}' not found")

    sightings = db.query(DogLocation).filter(DogLocation.dog_id == dog.id).order_by(DogLocation.recorded_at.desc()).all()
    sightings_data = []
    for s in sightings:
        sightings_data.append({
            "id": s.id,
            "lat": s.lat,
            "lng": s.lng,
            "address": s.address,
            "area": s.area,
            "city": s.city,
            "state": s.state,
            "recorded_by": s.recorded_by,
            "recorded_at": s.recorded_at.isoformat() if s.recorded_at else None,
            "note": s.note
        })

    if not sightings_data and dog.location_lat and dog.location_lng:
        sightings_data.append({
            "id": 0,
            "lat": dog.location_lat,
            "lng": dog.location_lng,
            "address": dog.location,
            "area": dog.location,
            "city": "Bengaluru",
            "state": "Karnataka",
            "recorded_by": dog.created_by,
            "recorded_at": dog.created_at.isoformat() if dog.created_at else None,
            "note": "Initial Registration Sighting"
        })

    vacs = db.query(Vaccination).filter(Vaccination.dog_id == dog.id).order_by(Vaccination.date_given.desc()).all()
    vac_data = []
    now = datetime.datetime.utcnow()
    for v in vacs:
        is_overdue = v.next_due < now if v.next_due else False
        is_due_soon = (v.next_due - now).days <= 30 if (v.next_due and not is_overdue) else False

        verifier_name = None
        if v.verified_by_user_id:
            verifier = db.query(User).filter(User.id == v.verified_by_user_id).first()
            if verifier: verifier_name = verifier.full_name or verifier.username

        vac_data.append({
            "id": v.id,
            "vaccine": v.vaccine,
            "date_given": v.date_given.isoformat() if v.date_given else None,
            "next_due": v.next_due.isoformat() if v.next_due else None,
            "given_by": v.given_by,
            "verified_by_user_id": v.verified_by_user_id,
            "verified_by_name": verifier_name,
            "notes": v.notes,
            "is_overdue": is_overdue,
            "is_due_soon": is_due_soon
        })

    events = db.query(HealthEvent).filter(HealthEvent.dog_id == dog.id).order_by(HealthEvent.date.desc()).all()
    events_data = []
    for ev in events:
        events_data.append({
            "id": ev.id,
            "type": ev.type,
            "description": ev.description,
            "source": ev.source,
            "photo": ev.photo,
            "created_by": ev.created_by,
            "date": ev.date.isoformat() if ev.date else None
        })

    creator_name = "System / Community"
    if dog.created_by:
        usr = db.query(User).filter(User.id == dog.created_by).first()
        if usr: creator_name = usr.full_name or usr.username

    last_audit = db.query(AuditLog).filter(
        AuditLog.entity_type == "dog",
        (AuditLog.entity_id == str(dog.public_code)) | (AuditLog.entity_id == str(dog.animal_id)) | (AuditLog.entity_id == str(dog.id))
    ).order_by(AuditLog.created_at.desc()).first()

    last_editor_info = None
    if last_audit:
        editor_user = db.query(User).filter(User.id == last_audit.actor_id).first() if last_audit.actor_id else None
        last_editor_info = {
            "action": last_audit.action,
            "actor_name": (editor_user.full_name or editor_user.username) if editor_user else "System",
            "date": last_audit.created_at.strftime("%Y-%m-%d %H:%M") if last_audit.created_at else None
        }

    return {
        "id": dog.id,
        "animal_id": dog.animal_id or f"DOG-{dog.id}",
        "public_code": dog.public_code,
        "name": dog.name or f"Stray {dog.public_code}",
        "sex": dog.sex or "unknown",
        "approx_age": dog.approx_age or "Unknown",
        "colour_markings": dog.colour_markings or "Not specified",
        "species": dog.species or "Dog",
        "breed": dog.breed or "Indian Pariah / Desi",
        "breed_source": dog.breed_source or "human",
        "temperament": dog.temperament or "Friendly",
        "sterilised": dog.sterilised or "unknown",
        "ear_notch": dog.ear_notch or False,
        "status": dog.health_status or dog.status or "Healthy / Sterilized",
        "health_status": dog.health_status or dog.status or "Healthy / Sterilized",
        "disease_name": dog.disease_name or "Normal",
        "location": dog.location or "Bengaluru",
        "location_lat": dog.location_lat or 12.9081,
        "location_lng": dog.location_lng or 77.5653,
        "image_url": dog.image_url or dog.primary_photo or "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=400&auto=format&fit=crop",
        "created_by": dog.created_by,
        "creator_name": creator_name,
        "created_at": dog.created_at.isoformat() if dog.created_at else None,
        "updated_at": dog.updated_at.isoformat() if dog.updated_at else None,
        "sightings": sightings_data,
        "vaccinations": vac_data,
        "health_events": events_data,
        "last_editor": last_editor_info
    }

# -----------------------------------------------------------------------------
# 6. UPDATE DOG PROFILE (RBAC Permission Checked, Audit Logged)
# -----------------------------------------------------------------------------
@dogs_router.put("/{dog_identifier}")
@dogs_router.patch("/{dog_identifier}")
def update_dog_profile(
    dog_identifier: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail="Dog record not found")

    # Permission check: Citizen can edit ONLY dogs they created
    if current_user.role == "citizen" and dog.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Citizens can only edit dogs they created."
        )

    before_state = {
        "name": dog.name, "breed": dog.breed, "health_status": dog.health_status,
        "location": dog.location, "sterilised": dog.sterilised, "ear_notch": dog.ear_notch
    }

    if "name" in data: dog.name = data["name"]
    if "breed" in data: dog.breed = data["breed"]
    if "sex" in data: dog.sex = data["sex"]
    if "approx_age" in data: dog.approx_age = data["approx_age"]
    if "colour_markings" in data: dog.colour_markings = data["colour_markings"]
    if "sterilised" in data: dog.sterilised = data["sterilised"]
    if "ear_notch" in data: dog.ear_notch = data["ear_notch"]
    if "status" in data or "health_status" in data:
        st = data.get("status") or data.get("health_status")
        dog.health_status = st
        dog.status = st
    if "health" in data or "disease_name" in data:
        dog.disease_name = data.get("health") or data.get("disease_name")
    if "location" in data: dog.location = data["location"]
    if "location_lat" in data: dog.location_lat = float(data["location_lat"])
    if "location_lng" in data: dog.location_lng = float(data["location_lng"])
    if "image_url" in data or "image" in data:
        img = data.get("image_url") or data.get("image")
        dog.image_url = img
        dog.primary_photo = img

    dog.updated_at = datetime.datetime.utcnow()
    db.commit()

    after_state = {
        "name": dog.name, "breed": dog.breed, "health_status": dog.health_status,
        "location": dog.location, "sterilised": dog.sterilised, "ear_notch": dog.ear_notch
    }

    audit(
        db=db,
        actor_id=current_user.id,
        action="update",
        entity_type="dog",
        entity_id=str(dog.public_code),
        before=before_state,
        after=after_state
    )

    return {"message": "Profile updated successfully", "public_code": dog.public_code, "dog_id": dog.id}

# -----------------------------------------------------------------------------
# 7. DELETE & RESTORE DOG PROFILE (Soft Delete + 10s Undo Window)
# -----------------------------------------------------------------------------
@dogs_router.delete("/{dog_identifier}")
def delete_dog_profile(
    dog_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog or dog.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Dog record not found")

    # Permission check: Citizen can delete ONLY dogs they created
    if current_user.role == "citizen" and dog.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Citizens can only delete dogs they created."
        )

    now = datetime.datetime.utcnow()
    dog.deleted_at = now
    dog.deleted_by = current_user.id
    db.commit()

    audit(
        db=db,
        actor_id=current_user.id,
        action="soft_delete",
        entity_type="dog",
        entity_id=str(dog.public_code),
        before={"deleted": False},
        after={"deleted": True, "deleted_at": now.isoformat(), "deleted_by": current_user.id}
    )

    return {
        "message": f"Dog record {dog.public_code} soft-deleted.",
        "public_code": dog.public_code,
        "deleted_at": now.isoformat(),
        "can_undo": True,
        "undo_window_seconds": 10
    }

@dogs_router.post("/{dog_identifier}/restore")
def restore_dog_profile(
    dog_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog or dog.deleted_at is None:
        raise HTTPException(status_code=404, detail="Soft-deleted dog record not found")

    now = datetime.datetime.utcnow()
    seconds_since_delete = (now - dog.deleted_at).total_seconds()

    # Permission check: Admin anytime, others within 10 seconds
    if current_user.role != "admin" and seconds_since_delete > 10.0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Undo restoration window (10 seconds) has expired ({int(seconds_since_delete)}s passed)."
        )

    dog.deleted_at = None
    dog.deleted_by = None
    db.commit()

    audit(
        db=db,
        actor_id=current_user.id,
        action="restore",
        entity_type="dog",
        entity_id=str(dog.public_code),
        before={"deleted": True},
        after={"deleted": False, "restored_by": current_user.id}
    )

    return {"message": f"Dog profile {dog.public_code} successfully restored.", "public_code": dog.public_code}

# -----------------------------------------------------------------------------
# 8. VACCINATIONS & HEALTH EVENTS ENDPOINTS
# -----------------------------------------------------------------------------
@dogs_router.post("/{dog_identifier}/vaccinations")
def add_dog_vaccination(
    dog_identifier: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail="Dog record not found")

    date_given = datetime.datetime.utcnow()
    if data.get("date_given"):
        try:
            date_given = datetime.datetime.fromisoformat(data["date_given"].replace('Z', ''))
        except ValueError:
            pass

    next_due = date_given + datetime.timedelta(days=365)
    if data.get("next_due"):
        try:
            next_due = datetime.datetime.fromisoformat(data["next_due"].replace('Z', ''))
        except ValueError:
            pass

    verified_by = None
    if current_user.role in ["ngo_staff", "admin", "govt_official"]:
        verified_by = current_user.id

    vac = Vaccination(
        dog_id=dog.id,
        vaccine=data.get("vaccine", "rabies"),
        date_given=date_given,
        next_due=next_due,
        given_by=data.get("given_by", current_user.full_name or current_user.username),
        verified_by_user_id=verified_by,
        notes=data.get("notes", "Vaccination record added")
    )
    db.add(vac)
    db.commit()
    db.refresh(vac)

    audit(
        db=db,
        actor_id=current_user.id,
        action="add_vaccination",
        entity_type="vaccination",
        entity_id=str(vac.id),
        before=None,
        after={"dog_id": dog.id, "vaccine": vac.vaccine, "verified_by": verified_by}
    )

    return {"message": "Vaccination recorded successfully", "vaccination_id": vac.id, "vaccine": vac.vaccine}

@dogs_router.post("/{dog_identifier}/health-events")
def add_dog_health_event(
    dog_identifier: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail="Dog record not found")

    ev = HealthEvent(
        dog_id=dog.id,
        date=datetime.datetime.utcnow(),
        type=data.get("type", "observation"),
        description=data.get("description", "Health observation recorded"),
        source=data.get("source", "human"),
        photo=data.get("photo"),
        created_by=current_user.id
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    audit(
        db=db,
        actor_id=current_user.id,
        action="add_health_event",
        entity_type="health_event",
        entity_id=str(ev.id),
        before=None,
        after={"dog_id": dog.id, "type": ev.type, "description": ev.description}
    )

    return {"message": "Health event recorded successfully", "event_id": ev.id}

# -----------------------------------------------------------------------------
# 9. LOCATION TIMELINE ENDPOINTS
# -----------------------------------------------------------------------------
@dogs_router.post("/{dog_identifier}/locations")
def add_dog_location(
    dog_identifier: str,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail=f"Dog record '{dog_identifier}' not found")

    lat = float(data.get("lat", 0))
    lng = float(data.get("lng", 0))

    if not (6.0 <= lat <= 37.5 and 68.0 <= lng <= 98.0):
        raise HTTPException(status_code=400, detail="Location coordinates must be within India (Latitude: 6.0 to 37.5, Longitude: 68.0 to 98.0)")

    loc = DogLocation(
        dog_id=dog.id,
        lat=lat,
        lng=lng,
        address=data.get("address"),
        area=data.get("area"),
        city=data.get("city", "Bengaluru"),
        state=data.get("state", "Karnataka"),
        recorded_by=current_user.id,
        note=data.get("note", "New sighting recorded"),
        recorded_at=datetime.datetime.utcnow()
    )
    db.add(loc)

    dog.location_lat = lat
    dog.location_lng = lng
    loc_name = data.get("address") or data.get("area") or f"{data.get('city', 'Bengaluru')}"
    if loc_name:
        dog.location = loc_name
    dog.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(loc)

    audit(
        db=db,
        actor_id=current_user.id,
        action="add_location",
        entity_type="dog_location",
        entity_id=str(loc.id),
        before=None,
        after={"dog_id": dog.id, "lat": lat, "lng": lng, "address": loc.address}
    )

    return {
        "message": "Sighting location recorded successfully",
        "location_id": loc.id,
        "dog_id": dog.id,
        "public_code": dog.public_code,
        "lat": loc.lat,
        "lng": loc.lng,
        "address": loc.address,
        "area": loc.area,
        "city": loc.city,
        "state": loc.state,
        "recorded_at": loc.recorded_at.isoformat()
    }

@dogs_router.patch("/{dog_identifier}/locations/{loc_id}")
def correct_dog_location(
    dog_identifier: str,
    loc_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    loc = db.query(DogLocation).filter(DogLocation.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location record #{loc_id} not found")

    before_state = {"lat": loc.lat, "lng": loc.lng, "address": loc.address, "note": loc.note}

    if "lat" in data and "lng" in data:
        lat = float(data["lat"])
        lng = float(data["lng"])
        if not (6.0 <= lat <= 37.5 and 68.0 <= lng <= 98.0):
            raise HTTPException(status_code=400, detail="Location coordinates must be within India (Latitude: 6.0 to 37.5, Longitude: 68.0 to 98.0)")
        loc.lat = lat
        loc.lng = lng

    if "address" in data: loc.address = data["address"]
    if "area" in data: loc.area = data["area"]
    if "city" in data: loc.city = data["city"]
    if "state" in data: loc.state = data["state"]
    if "note" in data: loc.note = data["note"]

    db.commit()
    db.refresh(loc)

    dog = db.query(Dog).filter(Dog.id == loc.dog_id).first()
    if dog:
        latest_loc = db.query(DogLocation).filter(DogLocation.dog_id == dog.id).order_by(DogLocation.recorded_at.desc()).first()
        if latest_loc and latest_loc.id == loc.id:
            dog.location_lat = loc.lat
            dog.location_lng = loc.lng
            if loc.address or loc.area:
                dog.location = loc.address or loc.area
            db.commit()

    after_state = {"lat": loc.lat, "lng": loc.lng, "address": loc.address, "note": loc.note}

    audit(
        db=db,
        actor_id=current_user.id,
        action="correct_location",
        entity_type="dog_location",
        entity_id=str(loc.id),
        before=before_state,
        after=after_state
    )

    return {
        "message": "Location entry corrected successfully",
        "location_id": loc.id,
        "lat": loc.lat,
        "lng": loc.lng,
        "address": loc.address,
        "area": loc.area,
        "city": loc.city,
        "state": loc.state
    }

@dogs_router.get("/{dog_identifier}/locations")
def get_dog_location_timeline(dog_identifier: str, db: Session = Depends(get_db)):
    dog = db.query(Dog).filter(
        (Dog.animal_id == dog_identifier) | 
        (Dog.public_code == dog_identifier) | 
        (Dog.id == (int(dog_identifier) if dog_identifier.isdigit() else -1))
    ).first()

    if not dog:
        raise HTTPException(status_code=404, detail=f"Dog record '{dog_identifier}' not found")

    locations = db.query(DogLocation).filter(DogLocation.dog_id == dog.id).order_by(DogLocation.recorded_at.desc()).all()

    timeline = []
    for l in locations:
        timeline.append({
            "id": l.id,
            "dog_id": l.dog_id,
            "lat": l.lat,
            "lng": l.lng,
            "address": l.address,
            "area": l.area,
            "city": l.city,
            "state": l.state,
            "recorded_by": l.recorded_by,
            "recorded_at": l.recorded_at.isoformat() if l.recorded_at else None,
            "note": l.note
        })

    if not timeline and dog.location_lat and dog.location_lng:
        timeline.append({
            "id": 0,
            "dog_id": dog.id,
            "lat": dog.location_lat,
            "lng": dog.location_lng,
            "address": dog.location,
            "area": dog.location,
            "city": "Bengaluru",
            "state": "Karnataka",
            "recorded_by": dog.created_by,
            "recorded_at": dog.created_at.isoformat() if dog.created_at else None,
            "note": "Initial Registration Sighting"
        })

    return timeline
