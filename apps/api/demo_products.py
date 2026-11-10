"""
Curated Demo Products Catalog & Provider.

Queries Firestore 'demo_products' collection.
Falls back to 3 core presets if Firestore is unreachable or unseeded.
"""

from typing import Any
from schemas import DemoProduct
from firebase import get_firestore_client

FALLBACK_DEMO_PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "keshabati-hair-oil",
        "name": "Keshabati Cold-Pressed Onion & Black Seed Hair Oil",
        "category": "Skincare",
        "description": "100% natural cold-pressed hair oil with red onion extract, kalonji, and rosemary essential oil. Reduces hair fall and repairs roots in 3 weeks without any greasy buildup.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1608248597359-58a5e8ff7174?auto=format&fit=crop&w=600&q=80",
        "order": 1,
    },
    {
        "id": "sundarban-wild-honey",
        "name": "Sundarban Raw Wildflower Honey",
        "category": "Food & Beverage",
        "description": "Unpasteurized raw honey harvested ethically from deep mangrove forests in the Sundarbans. Rich in natural floral enzymes, antioxidants, and pure raw nectar.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": "https://images.unsplash.com/photo-1587049352846-4a222e784d38?auto=format&fit=crop&w=600&q=80",
        "order": 2,
    },
    {
        "id": "saffron-glow-serum",
        "name": "Kashmiri Saffron & 5% Niacinamide Radiance Serum",
        "category": "Skincare",
        "description": "Lightweight brightening daytime serum blending real Kashmiri saffron extract with 5% niacinamide and hyaluronic acid to fade hyperpigmentation and restore a natural glow.",
        "market": "Global",
        "language": "en",
        "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=600&q=80",
        "order": 3,
    },
]

# In-memory cache for demo products
_cached_demo_products: list[DemoProduct] | None = None


def clear_demo_products_cache() -> None:
    global _cached_demo_products
    _cached_demo_products = None


async def get_demo_products_catalog() -> list[DemoProduct]:
    """
    Fetches demo products from Firestore 'demo_products' collection.
    If Firestore has records, returns them.
    If Firestore is empty or unreachable, returns 3 core fallback products.
    """
    global _cached_demo_products
    if _cached_demo_products is not None:
        return _cached_demo_products

    try:
        db = get_firestore_client()
        docs = await db.collection("demo_products").order_by("order").get()
        if docs and len(docs) > 0:
            products: list[DemoProduct] = []
            for doc in docs:
                data = doc.to_dict()
                products.append(DemoProduct(**data))
            if products:
                _cached_demo_products = products
                return products
    except Exception as e:
        print(f"Notice: Firestore demo_products lookup fell back to 3 presets: {e}")

    # Fallback to only 3 core products if Firestore is unseeded
    fallback = [DemoProduct(**p) for p in FALLBACK_DEMO_PRODUCTS]
    _cached_demo_products = fallback
    return fallback


async def find_demo_product(product_id: str) -> DemoProduct | None:
    """Finds a demo product by ID from Firestore or fallback."""
    catalog = await get_demo_products_catalog()
    for p in catalog:
        if p.id == product_id:
            return p
    return None
