"""
CLI Script to Seed Firestore with Demo Products and Initial Access Codes.

Usage:
  cd apps/api
  .venv/bin/python scripts/seed_firestore.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from firebase import get_firestore_client
from google.cloud import firestore

INITIAL_ACCESS_CODES = [
    {
        "code": "DEMO1",
        "owner_name": "Demo User",
        "company": "Creator Beta",
        "active": True,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "generation_count": 0,
    },
    {
        "code": "DHAKA",
        "owner_name": "Dhaka Tester",
        "company": "Chaldal / Independent",
        "active": True,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "generation_count": 0,
    },
    {
        "code": "BETA1",
        "owner_name": "Beta VIP",
        "company": "VIP Studio",
        "active": True,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "generation_count": 0,
    },
    {
        "code": "UG001",
        "owner_name": "UG Founder",
        "company": "UG-Scripts Core",
        "active": True,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "generation_count": 0,
    },
    {
        "code": "BETA-DHAKA-01",
        "owner_name": "Demo Tester",
        "company": "Chaldal / Independent",
        "active": True,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "generation_count": 0,
    },
]

ALL_12_DEMO_PRODUCTS = [
    {
        "id": "keshabati-hair-oil",
        "name": "Keshabati Cold-Pressed Onion & Black Seed Hair Oil",
        "category": "Skincare",
        "description": "100% natural cold-pressed hair oil with red onion extract, kalonji, and rosemary essential oil. Reduces postpartum and stress-induced hair fall in 3 weeks without any greasy buildup.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1608248597359-58a5e8ff7174?auto=format&fit=crop&w=600&q=80",
        "order": 1,
    },
    {
        "id": "sundarban-wild-honey",
        "name": "Sundarban Raw Kalijira Wildflower Honey",
        "category": "Food & Beverage",
        "description": "Unpasteurized, unprocessed deep-forest raw honey harvested ethically by traditional Mowali honey collectors in the Sundarbans mangrove. Packed with live enzymes and natural pollen.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=600&q=80",
        "order": 2,
    },
    {
        "id": "dhaka-leather-sneaker",
        "name": "Dacca Artisanal Full-Grain Leather Sneakers",
        "category": "Fashion",
        "description": "Handcrafted minimalist low-top sneakers made from vegetable-tanned Bangladeshi cowhide leather with shock-absorbing memory foam insoles. Built for all-day city walking.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=600&q=80",
        "order": 3,
    },
    {
        "id": "acousticwave-earbuds",
        "name": "AcousticWave Pro ANC Wireless Earbuds",
        "category": "Tech / Gadgets",
        "description": "Active noise cancelling wireless earbuds with 42dB ambient sound reduction, quad-mic ENC for crystal-clear calls in Dhaka traffic, and 36-hour total battery life.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80",
        "order": 4,
    },
    {
        "id": "saffron-glow-serum",
        "name": "Kashmiri Saffron & 5% Niacinamide Radiance Serum",
        "category": "Skincare",
        "description": "Lightweight daytime serum blending real Kashmiri saffron stigma extract with niacinamide and alpha arbutin. Fades stubborn dark spots, acne hyperpigmentation, and sun tanning.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=600&q=80",
        "order": 5,
    },
    {
        "id": "bengal-linen-shirt",
        "name": "Bengal Breeze 100% Breathable Linen Shirt",
        "category": "Fashion",
        "description": "Relaxed-fit Cuban collar casual shirt woven from pure European flax linen. Ultra-breathable, moisture-wicking fabric designed specifically for hot and humid tropical summers.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=600&q=80",
        "order": 6,
    },
    {
        "id": "zenith-mesh-chair",
        "name": "Zenith Posture Pro Ergonomic Mesh Chair",
        "category": "Home & Living",
        "description": "Engineered home office chair with 3D adaptive lumbar support, 4D adjustable armrests, and high-tensile breathable Korean mesh that eliminates lower back stiffness.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1580481077195-c290c0b32252?auto=format&fit=crop&w=600&q=80",
        "order": 7,
    },
    {
        "id": "hydrabarrier-water-gel",
        "name": "HydraBarrier 5-Ceramide Water Gel Moisturizer",
        "category": "Skincare",
        "description": "Oil-free gel moisturizer powered by 5 essential bio-identical ceramides, multi-molecular hyaluronic acid, and centella asiatica. Restores skin moisture barrier without clogging pores.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=600&q=80",
        "order": 8,
    },
    {
        "id": "pulsetitan-smart-ring",
        "name": "PulseTitan Titanium Sleep & HRV Smart Ring",
        "category": "Tech / Gadgets",
        "description": "Medical-grade lightweight titanium smart ring tracking sleep stages, heart rate variability (HRV), skin temperature deviations, and readiness score with zero screen distractions.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1605100804763-247f67b3557e?auto=format&fit=crop&w=600&q=80",
        "order": 9,
    },
    {
        "id": "ceremonial-matcha-tin",
        "name": "Uji First-Harvest Ceremonial Grade Matcha",
        "category": "Food & Beverage",
        "description": "Stone-ground green tea powder from shade-grown spring tea leaves in Uji, Kyoto. Smooth umami flavor with zero bitterness, offering clean sustained alertness without coffee jitters.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80",
        "order": 10,
    },
    {
        "id": "damascus-chef-knife",
        "name": "Kurogane 8-Inch Damascus Steel Chef Knife",
        "category": "Home & Living",
        "description": "67-layer hammered Damascus steel kitchen knife with an ultra-sharp 15-degree double-bevel cutting edge and ergonomic pakkawood handle for effortless vegetable and meat slicing.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1593618998160-e34014e67546?auto=format&fit=crop&w=600&q=80",
        "order": 11,
    },
    {
        "id": "aeroflex-leggings",
        "name": "AeroFlex Squat-Proof Seamless High-Rise Leggings",
        "category": "Fashion",
        "description": "Buttery-soft compression gym leggings engineered with four-way stretch interlock knit, non-slip ribbed waistband, and zero center seam to prevent chafing during intense workouts.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1506617564039-2f3b650b7010?auto=format&fit=crop&w=600&q=80",
        "order": 12,
    },
]


async def seed():
    print(f"Connecting to Firestore for project '{os.environ.get('GOOGLE_CLOUD_PROJECT', 'ugstar')}'...")
    db = get_firestore_client()

    # Seed access codes
    for item in INITIAL_ACCESS_CODES:
        code = item["code"]
        doc_ref = db.collection("access_codes").document(code)
        await doc_ref.set({
            **item,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_used_at": None,
        })
        print(f"✓ Seeded access code: {code}")

    # Seed demo products
    for p in ALL_12_DEMO_PRODUCTS:
        slug = p["id"]
        doc_ref = db.collection("demo_products").document(slug)
        await doc_ref.set(p)
        print(f"✓ Seeded demo product: {slug} ({p['name']})")

    print("\n✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
