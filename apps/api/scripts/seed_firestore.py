"""
CLI Script to Seed Firestore with Demo Products and Initial Access Codes.

De-seeds previous sample products from Firestore (except Kashmiri Saffron Serum
and Bengal Breeze Linen Shirt) and populates the 12 evaluation products from
apps/api/evals/products with their corresponding images.

Usage:
  cd apps/api
  .venv/bin/python scripts/seed_firestore.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from firebase import get_firestore_client
from google.cloud import firestore

GCS_IMAGE_BASE_URL = "https://storage.googleapis.com/ugstar-demo-assets/demo-products"

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

# The 2 existing products specifically retained by user request
KEPT_DEMO_PRODUCTS = [
    {
        "id": "saffron-glow-serum",
        "name": "Kashmiri Saffron & 5% Niacinamide Radiance Serum",
        "category": "Skincare",
        "description": "Lightweight daytime serum blending real Kashmiri saffron stigma extract with niacinamide and alpha arbutin. Fades stubborn dark spots, acne hyperpigmentation, and sun tanning.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": f"{GCS_IMAGE_BASE_URL}/kashmiri_saffron_serum.jpg",
    },
    {
        "id": "bengal-linen-shirt",
        "name": "Bengal Breeze 100% Breathable Linen Shirt",
        "category": "Fashion",
        "description": "Relaxed-fit Cuban collar casual shirt woven from pure European flax linen. Ultra-breathable, moisture-wicking fabric designed specifically for hot and humid tropical summers.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": f"{GCS_IMAGE_BASE_URL}/bengal_linen_shirt.jpg",
    },
]


def load_eval_products() -> list[dict[str, Any]]:
    """Loads and formats the 12 curated eval products from apps/api/evals/products."""
    products_dir = Path(__file__).resolve().parent.parent / "evals" / "products"
    if not products_dir.exists():
        raise FileNotFoundError(f"Evals products directory not found: {products_dir}")

    eval_files = sorted(products_dir.glob("*.json"))
    items: list[dict[str, Any]] = []

    for file_path in eval_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"Skipping invalid json {file_path}: {e}")
            continue

        image_filename = raw.get("image_filename", "")
        image_url = f"{GCS_IMAGE_BASE_URL}/{image_filename}" if image_filename else ""

        items.append({
            "id": raw["id"],
            "name": raw["name"],
            "category": raw.get("category", "General"),
            "description": raw.get("description", ""),
            "market": raw.get("market", "Bangladesh"),
            "language": raw.get("default_language", "bn"),
            "image_url": image_url,
        })

    return items


def get_all_demo_products() -> list[dict[str, Any]]:
    """Builds the complete ordered catalog: 12 eval products + 2 kept products."""
    eval_products = load_eval_products()
    combined = eval_products + KEPT_DEMO_PRODUCTS

    for idx, p in enumerate(combined, start=1):
        p["order"] = idx

    return combined


async def seed():
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "ugstar")
    print(f"Connecting to Firestore for project '{project_id}'...")
    db = get_firestore_client()

    # 1. Seed Access Codes
    print("\n--- Seeding Access Codes ---")
    for item in INITIAL_ACCESS_CODES:
        code = item["code"]
        doc_ref = db.collection("access_codes").document(code)
        await doc_ref.set({
            **item,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_used_at": None,
        })
        print(f"✓ Seeded access code: {code}")

    # 2. Build target product catalog
    target_products = get_all_demo_products()
    target_ids = {p["id"] for p in target_products}

    print(f"\n--- De-seeding Removed Products (Target: {len(target_products)} products) ---")
    demo_col = db.collection("demo_products")
    existing_docs = await demo_col.get()

    deleted_count = 0
    for doc in existing_docs:
        if doc.id not in target_ids:
            await demo_col.document(doc.id).delete()
            print(f"🗑 De-seeded old product: {doc.id}")
            deleted_count += 1

    if deleted_count == 0:
        print("No obsolete products found in Firestore.")
    else:
        print(f"Successfully removed {deleted_count} obsolete products.")

    # 3. Seed new/updated demo products
    print("\n--- Seeding Updated Demo Products ---")
    for p in target_products:
        slug = p["id"]
        doc_ref = demo_col.document(slug)
        await doc_ref.set(p)
        print(f"✓ Seeded demo product: #{p['order']} {slug} ({p['name']})")

    print(f"\n✅ Firestore seeding completed! Total demo products in shelf: {len(target_products)}")


if __name__ == "__main__":
    asyncio.run(seed())
