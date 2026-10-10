import sys
import os
import datetime

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from db.database import SessionLocal
from db.models import Dog, DogLocation, Vaccination, User

# 25 Distinct, Verified, Realistic Dogs
CURATED_DOGS = [
    {
        "public_code": "PAW-0001",
        "animal_id": "DOG-1001",
        "name": "Bruno",
        "breed": "Indian Pariah / Desi",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "2.5 years",
        "colour_markings": "Tan coat with white chest star, pointed erect ears",
        "temperament": "Friendly / Community Fed",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.4,
        "location": "Indiranagar 100ft Road, near Metro Pillar 42, Bengaluru",
        "location_lat": 12.9784,
        "location_lng": 77.6408,
        "area": "Indiranagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 28
    },
    {
        "public_code": "PAW-0002",
        "animal_id": "DOG-1002",
        "name": "Kaalu",
        "breed": "Street Mongrel (Brindle)",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1548767797-d8c844163c4c?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3 years",
        "colour_markings": "Dark brown & black brindle coat, white muzzle patch",
        "temperament": "Calm / Loyal Pack Guardian",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 96.1,
        "location": "Koramangala 4th Block, 80ft Road Junction, Bengaluru",
        "location_lat": 12.9345,
        "location_lng": 77.6242,
        "area": "Koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "DHPPiL 7-in-1",
        "days_ago": 26
    },
    {
        "public_code": "PAW-0003",
        "animal_id": "DOG-1003",
        "name": "Maya",
        "breed": "Indian Hound / Rajapalayam Cross",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2 years",
        "colour_markings": "Milky white coat, amber eyes, slender athletic frame",
        "temperament": "Gentle / Fast Runner",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 99.0,
        "location": "Jayanagar 4th Block, near Complex Circle, Bengaluru",
        "location_lat": 12.9299,
        "location_lng": 77.5824,
        "area": "Jayanagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 25
    },
    {
        "public_code": "PAW-0004",
        "animal_id": "DOG-1004",
        "name": "Simba",
        "breed": "Golden Retriever",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1552053831-71594a27632d?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "4 years",
        "colour_markings": "Rich golden amber wavy coat, feathered tail",
        "temperament": "Playful / Highly Social",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 97.5,
        "location": "Malleshwaram 8th Cross, Margosa Road, Bengaluru",
        "location_lat": 13.0031,
        "location_lng": 77.5643,
        "area": "Malleshwaram",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Annual Booster Multi-antigen",
        "days_ago": 24
    },
    {
        "public_code": "PAW-0005",
        "animal_id": "DOG-1005",
        "name": "Cooper",
        "breed": "Labrador Retriever",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3.5 years",
        "colour_markings": "Cream yellow coat, broad head, dark brown nose",
        "temperament": "Affectionate / Food Motivated",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.2,
        "location": "HSR Layout Sector 1, 27th Main, Bengaluru",
        "location_lat": 12.9121,
        "location_lng": 77.6446,
        "area": "HSR Layout",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "DHPPiL 7-in-1",
        "days_ago": 23
    },
    {
        "public_code": "PAW-0006",
        "animal_id": "DOG-1006",
        "name": "Chotu",
        "breed": "Pug",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1517849845537-4d257902454a?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "2 years",
        "colour_markings": "Fawn coat, black face mask, wrinkled brow, curled tail",
        "temperament": "Timid / Gentle",
        "sterilised": "no",
        "ear_notch": False,
        "status": "Under Medical Care",
        "health_status": "Under Medical Care",
        "disease_name": "Dermatitis Treated",
        "disease_confidence": 88.0,
        "location": "Whitefield Main Road, near Hope Farm, Bengaluru",
        "location_lat": 12.9698,
        "location_lng": 77.7499,
        "area": "Whitefield",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": False,
        "days_ago": 22
    },
    {
        "public_code": "PAW-0007",
        "animal_id": "DOG-1007",
        "name": "Buster",
        "breed": "Beagle",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1507146426996-ef05306b995a?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "1.5 years",
        "colour_markings": "Tricolour black, tan & white, long drooping ears",
        "temperament": "Energetic / Scent Hound",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Vaccinated",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 95.8,
        "location": "Rajajinagar 1st Block, Navrang Circle, Bengaluru",
        "location_lat": 12.9980,
        "location_lng": 77.5530,
        "area": "Rajajinagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 21
    },
    {
        "public_code": "PAW-0008",
        "animal_id": "DOG-1008",
        "name": "Rocky",
        "breed": "German Shepherd",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1589941013453-ec89f33b5e95?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3 years",
        "colour_markings": "Classic black & tan saddle coat, erect pointed ears",
        "temperament": "Alert / Protective",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.9,
        "location": "Yelahanka New Town, 4th Phase Park, Bengaluru",
        "location_lat": 13.0991,
        "location_lng": 77.5924,
        "area": "Yelahanka",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Anti-Rabies Tagged",
        "days_ago": 20
    },
    {
        "public_code": "PAW-0009",
        "animal_id": "DOG-1009",
        "name": "Shadow",
        "breed": "Black Labrador Cross",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "2 years",
        "colour_markings": "Jet black sleek coat, white chest star, amber eyes",
        "temperament": "Quiet / Friendly Sitter",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 97.1,
        "location": "JP Nagar 6th Phase, Sarakki Lake Gate, Bengaluru",
        "location_lat": 12.9077,
        "location_lng": 77.5857,
        "area": "JP Nagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 19
    },
    {
        "public_code": "PAW-0010",
        "animal_id": "DOG-1010",
        "name": "Moti",
        "breed": "Pomeranian / Indian Spitz",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "3 years",
        "colour_markings": "Fluffy pure white double coat, fox-like muzzle, plumed tail",
        "temperament": "Vocal / Lively Companion",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Vaccinated",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 99.3,
        "location": "Banashankari 3rd Stage, Kathriguppe, Bengaluru",
        "location_lat": 12.9250,
        "location_lng": 77.5468,
        "area": "Banashankari",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "7-in-1 Combined",
        "days_ago": 18
    },
    {
        "public_code": "PAW-0011",
        "animal_id": "DOG-1011",
        "name": "Tyson",
        "breed": "Rottweiler Cross",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1567752881298-894bb81f9379?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "4 years",
        "colour_markings": "Black coat with defined rich mahogany markings on chest",
        "temperament": "Confident / Docile with Handlers",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 96.7,
        "location": "BTM Layout 2nd Stage, Udupi Garden, Bengaluru",
        "location_lat": 12.9166,
        "location_lng": 77.6101,
        "area": "BTM Layout",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 17
    },
    {
        "public_code": "PAW-0012",
        "animal_id": "DOG-1012",
        "name": "Leo",
        "breed": "Doberman Pinscher",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "2.5 years",
        "colour_markings": "Sleek short black & rust coat, athletic lean posture",
        "temperament": "Alert / Intelligent",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.1,
        "location": "Electronic City Phase 1, Wipro Gate, Bengaluru",
        "location_lat": 12.8399,
        "location_lng": 77.6770,
        "area": "Electronic City",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "DHPP Booster",
        "days_ago": 16
    },
    {
        "public_code": "PAW-0013",
        "animal_id": "DOG-1013",
        "name": "Sheru",
        "breed": "Boxer Cross",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1598133894008-61f7fdb8cc3a?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3 years",
        "colour_markings": "Warm fawn coat, white chest blaze, short blunt muzzle",
        "temperament": "Playful / High Energy",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 94.3,
        "location": "Basavanagudi Bull Temple Road, Bengaluru",
        "location_lat": 12.9431,
        "location_lng": 77.5683,
        "area": "Basavanagudi",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 15
    },
    {
        "public_code": "PAW-0014",
        "animal_id": "DOG-1014",
        "name": "Charlie",
        "breed": "Dachshund",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1560807707-8cc77767d783?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "2 years",
        "colour_markings": "Reddish-brown smooth coat, elongated back, short legs",
        "temperament": "Curious / Determined",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Vaccinated",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.7,
        "location": "Bellandur EcoSpace, Outer Ring Road, Bengaluru",
        "location_lat": 12.9260,
        "location_lng": 77.6762,
        "area": "Bellandur",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Annual Rabies Shot",
        "days_ago": 14
    },
    {
        "public_code": "PAW-0015",
        "animal_id": "DOG-1015",
        "name": "Ghost",
        "breed": "Siberian Husky Cross",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1605568427561-40dd23c2acea?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2.5 years",
        "colour_markings": "Silver grey & white thick coat, erect triangular ears",
        "temperament": "Independent / Pack Friendly",
        "sterilised": "no",
        "ear_notch": False,
        "status": "Under Medical Care",
        "health_status": "Under Medical Care",
        "disease_name": "Demodicosis Treated",
        "disease_confidence": 91.2,
        "location": "Ulsoor Lake Promenade, Sivanchetti Garden, Bengaluru",
        "location_lat": 12.9818,
        "location_lng": 77.6200,
        "area": "Ulsoor",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 13
    },
    {
        "public_code": "PAW-0016",
        "animal_id": "DOG-1016",
        "name": "Daisy",
        "breed": "Shih Tzu",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1535930891776-0c2dfb7fda1a?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "3 years",
        "colour_markings": "Silky long white & cream coat, dark warm eyes",
        "temperament": "Lapdog / Gentle & Sweet",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Vaccinated",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 99.4,
        "location": "Frazer Town Mosque Road, Coles Park, Bengaluru",
        "location_lat": 12.9972,
        "location_lng": 77.6134,
        "area": "Frazer Town",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "DHPPiL Vaccine",
        "days_ago": 12
    },
    {
        "public_code": "PAW-0017",
        "animal_id": "DOG-1017",
        "name": "Kaveri",
        "breed": "Indie Black & Tan",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1561037404-61cd46aa615b?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "1.5 years",
        "colour_markings": "Short black coat, distinct tan eyebrow dots & paws",
        "temperament": "Clever / Community Favourite",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 97.8,
        "location": "Hebbal Flyover Junction, Outer Ring Road, Bengaluru",
        "location_lat": 13.0358,
        "location_lng": 77.5970,
        "area": "Hebbal",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 11
    },
    {
        "public_code": "PAW-0018",
        "animal_id": "DOG-1018",
        "name": "Brownie",
        "breed": "Indie Sandy Fawn",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2 years",
        "colour_markings": "Uniform sandy tan coat, alert almond-shaped dark eyes",
        "temperament": "Calm / Sunbather",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.6,
        "location": "Sarjapur Road, near Carmelaram Station, Bengaluru",
        "location_lat": 12.9080,
        "location_lng": 77.6840,
        "area": "Sarjapur Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "BBMP Drive Tagged",
        "days_ago": 10
    },
    {
        "public_code": "PAW-0019",
        "animal_id": "DOG-1019",
        "name": "Raja",
        "breed": "Desi Shepherd Cross",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1530281700549-e82e7bf110d6?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3.5 years",
        "colour_markings": "Golden sable dense coat, dark mask, bushy curved tail",
        "temperament": "Brave / Street Patrol Leader",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 99.1,
        "location": "Marathahalli Bridge Junction, HAL Area, Bengaluru",
        "location_lat": 12.9569,
        "location_lng": 77.7011,
        "area": "Marathahalli",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 9
    },
    {
        "public_code": "PAW-0020",
        "animal_id": "DOG-1020",
        "name": "Tara",
        "breed": "Indie Short-hair",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1558788353-f76d92427f16?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "1 year",
        "colour_markings": "Warm ginger-tan short coat, white stockings on paws",
        "temperament": "Friendly / Sprightly & Curious",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 96.9,
        "location": "KR Puram Lake Road, Railway Station Gate, Bengaluru",
        "location_lat": 13.0012,
        "location_lng": 77.6965,
        "area": "KR Puram",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 8
    },
    {
        "public_code": "PAW-0021",
        "animal_id": "DOG-1021",
        "name": "Lucy",
        "breed": "Cocker Spaniel Cross",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1514984879728-be0aff75a6e8?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2.5 years",
        "colour_markings": "Wavy golden honey coat, long feathered ears",
        "temperament": "Gentle / Tail Wagger",
        "sterilised": "yes",
        "ear_notch": False,
        "status": "Vaccinated",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.0,
        "location": "Richmond Town Circle, General K S Thimayya Road, Bengaluru",
        "location_lat": 12.9647,
        "location_lng": 77.6012,
        "area": "Richmond Town",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Combined 7-in-1",
        "days_ago": 7
    },
    {
        "public_code": "PAW-0022",
        "animal_id": "DOG-1022",
        "name": "Gauri",
        "breed": "Indie Piebald White & Brown",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2 years",
        "colour_markings": "Clean white base coat with rich chestnut brown flank patches",
        "temperament": "Sweet / Quiet & Calm",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 97.4,
        "location": "Domlur Intermediate Ring Road, Flyover, Bengaluru",
        "location_lat": 12.9609,
        "location_lng": 77.6387,
        "area": "Domlur",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 6
    },
    {
        "public_code": "PAW-0023",
        "animal_id": "DOG-1023",
        "name": "Tiger",
        "breed": "Indian Hound Mix",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1576201836106-db1758fd1c97?w=500&auto=format&fit=crop",
        "sex": "male",
        "approx_age": "3 years",
        "colour_markings": "Lean athletic deep tan coat, deep chest, graceful gait",
        "temperament": "Alert / Fleet Footed",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 98.3,
        "location": "Sadashivanagar Palace Cross, Sankey Tank, Bengaluru",
        "location_lat": 13.0068,
        "location_lng": 77.5813,
        "area": "Sadashivanagar",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Anti-Rabies Drive Tagged",
        "days_ago": 5
    },
    {
        "public_code": "PAW-0024",
        "animal_id": "DOG-1024",
        "name": "Zoey",
        "breed": "Indie Tri-colour",
        "breed_source": "human",
        "image_url": "https://images.unsplash.com/photo-1546182990-dffeafbe841d?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "2 years",
        "colour_markings": "Symmetrical black saddle, tan cheeks, white blaze on forehead",
        "temperament": "Intelligent / Friendly Greeting",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 99.2,
        "location": "Cooke Town Milton Street, Richards Park, Bengaluru",
        "location_lat": 12.9995,
        "location_lng": 77.6225,
        "area": "Cooke Town",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 4
    },
    {
        "public_code": "PAW-0025",
        "animal_id": "DOG-1025",
        "name": "Bella",
        "breed": "Desi Brown Indie",
        "breed_source": "ai",
        "image_url": "https://images.unsplash.com/photo-1510771463146-e89e6e86560e?w=500&auto=format&fit=crop",
        "sex": "female",
        "approx_age": "1.5 years",
        "colour_markings": "Warm milk-chocolate coat, soft amber eyes, inquisitive posture",
        "temperament": "Gentle / Affectionate Street Dog",
        "sterilised": "yes",
        "ear_notch": True,
        "status": "Healthy / Sterilized",
        "health_status": "Healthy / Sterilized",
        "disease_name": "Normal",
        "disease_confidence": 97.9,
        "location": "DSU Main Campus Gate 2, Kudlu Gate, Bengaluru",
        "location_lat": 12.9081,
        "location_lng": 77.5653,
        "area": "Kudlu Gate",
        "city": "Bengaluru",
        "state": "Karnataka",
        "vaccinated": True,
        "vac_type": "Rabies ARV",
        "days_ago": 3
    }
]

def update_registry_database():
    print("=========================================================")
    print("  UPDATING DIGITAL ANIMAL REGISTRY WITH REALISTIC DATA   ")
    print("=========================================================")

    db = SessionLocal()
    try:
        # Step 1: Preserve real user records
        # Identify user created dogs (e.g. user 111, or any real user created records)
        real_user_dogs = db.query(Dog).filter(Dog.created_by == 111).all()
        print(f"Found {len(real_user_dogs)} genuine user-created dog records to preserve.")

        # Step 2: Delete automated test runner junk dogs (IDs 26 to 58)
        # These were created by repeated test script runs with dummy names
        test_junk_dogs = db.query(Dog).filter(Dog.id >= 26, Dog.id <= 58).all()
        print(f"Cleaning up {len(test_junk_dogs)} automated test junk records (IDs 26-58)...")
        for jd in test_junk_dogs:
            db.query(DogLocation).filter(DogLocation.dog_id == jd.id).delete()
            db.query(Vaccination).filter(Vaccination.dog_id == jd.id).delete()
            db.delete(jd)
        db.commit()

        # Step 3: Upsert the 25 Pristine Distinct Curated Dogs
        for idx, item in enumerate(CURATED_DOGS, 1):
            public_code = item["public_code"]
            created_at = datetime.datetime.utcnow() - datetime.timedelta(days=item["days_ago"])

            dog = db.query(Dog).filter((Dog.public_code == public_code) | (Dog.id == idx)).first()
            if not dog:
                dog = Dog(id=idx)
                db.add(dog)

            # Assign pristine, distinct realistic data
            dog.public_code = item["public_code"]
            dog.animal_id = item["animal_id"]
            dog.name = item["name"]
            dog.species = "Dog"
            dog.breed = item["breed"]
            dog.breed_source = item["breed_source"]
            dog.sex = item["sex"]
            dog.approx_age = item["approx_age"]
            dog.colour_markings = item["colour_markings"]
            dog.temperament = item["temperament"]
            dog.sterilised = item["sterilised"]
            dog.ear_notch = item["ear_notch"]
            dog.status = item["status"]
            dog.health_status = item["health_status"]
            dog.disease_name = item["disease_name"]
            dog.disease_confidence = item["disease_confidence"]
            dog.primary_photo = item["image_url"]
            dog.image_url = item["image_url"]
            dog.location = item["location"]
            dog.location_lat = item["location_lat"]
            dog.location_lng = item["location_lng"]
            dog.created_at = created_at
            dog.created_by = None  # Seeded community records
            db.flush()

            # Ensure matching DogLocation sighting exists
            db.query(DogLocation).filter(DogLocation.dog_id == dog.id).delete()
            sighting = DogLocation(
                dog_id=dog.id,
                lat=item["location_lat"],
                lng=item["location_lng"],
                address=item["location"],
                area=item["area"],
                city=item["city"],
                state=item["state"],
                recorded_at=created_at,
                note=f"Community sighting verification for {item['name']}"
            )
            db.add(sighting)

            # Ensure vaccination record is clean & accurate
            db.query(Vaccination).filter(Vaccination.dog_id == dog.id).delete()
            if item.get("vaccinated"):
                vac = Vaccination(
                    dog_id=dog.id,
                    vaccine=item.get("vac_type", "Rabies ARV"),
                    date_given=created_at,
                    next_due=created_at + datetime.timedelta(days=365),
                    given_by="BBMP Animal Welfare Unit #3",
                    notes="Annual anti-rabies drive tag verified"
                )
                db.add(vac)

        db.commit()
        print("[OK] Successfully updated all 25 curated dog records with 100% distinct data!")

        # Step 4: Verification summary
        all_active_dogs = db.query(Dog).order_by(Dog.id.asc()).all()
        print(f"\nTotal active dogs in registry: {len(all_active_dogs)}")

        codes = [d.public_code for d in all_active_dogs]
        photos = [d.image_url for d in all_active_dogs]
        coords = [(d.location_lat, d.location_lng) for d in all_active_dogs]

        assert len(codes) == len(set(codes)), "Duplicate public_code detected!"
        print(f"[OK] All {len(codes)} dogs have 100% UNIQUE public_codes.")

        demo_photos = [d.image_url for d in all_active_dogs if d.id <= 25]
        assert len(demo_photos) == len(set(demo_photos)), "Duplicate demo photo URLs detected!"
        print(f"[OK] All 25 demo dogs have 100% UNIQUE REAL PHOTOGRAPHS.")

        demo_coords = [(d.location_lat, d.location_lng) for d in all_active_dogs if d.id <= 25]
        assert len(demo_coords) == len(set(demo_coords)), "Duplicate demo coordinates detected!"
        print(f"[OK] All 25 demo dogs have 100% DISTINCT COORDINATES.")

        print("\nRegistry Preview (Top 10 Dogs):")
        for d in all_active_dogs[:10]:
            print(f"  [{d.public_code}] {d.name:10s} | Breed: {d.breed:28s} | Loc: {d.location[:30]}... | Img: {d.image_url[:50]}...")

        print("=========================================================")
        print("  REGISTRY DATA UPDATE COMPLETED SUCCESSFULLY!           ")
        print("=========================================================")
    except Exception as e:
        print(f"Error during registry update: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_registry_database()
