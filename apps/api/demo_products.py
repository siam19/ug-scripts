"""
Curated Demo Products Catalog & Provider.

Queries Firestore 'demo_products' collection.
Falls back to core presets if Firestore is unreachable or unseeded.
"""

from typing import Any
from schemas import DemoProduct
from firebase import get_firestore_client

GCS_IMAGE_BASE_URL = "https://storage.googleapis.com/ugstar-demo-assets/demo-products"

FALLBACK_DEMO_PRODUCTS: list[dict[str, Any]] = [
    {
        "id": "radhuni-biryani-masala",
        "name": "Radhuni Biryani Masala (40g)",
        "category": "Food & Beverage",
        "description": "Aromatic blend of traditional spices formulated according to authentic biryani recipes in a convenient 40gm pack. Makes rich, fragrant mutton, beef, and chicken biryani at home with ease.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": f"{GCS_IMAGE_BASE_URL}/01_radhuni_biryani_masala.webp",
        "order": 1,
    },
    {
        "id": "taaga-female-dress",
        "name": "Taaga Flared Maroon Cotton Long Dress",
        "category": "Fashion",
        "description": "Contemporary flared long dress from Aarong's Taaga sub-brand crafted from 100% breathable cotton in rich maroon with screen-printed motifs. Tailored for comfort in tropical heat.",
        "market": "Bangladesh",
        "language": "bn",
        "image_url": f"{GCS_IMAGE_BASE_URL}/06_taaga_female_dress.webp",
        "order": 2,
    },
    {
        "id": "saffron-glow-serum",
        "name": "Kashmiri Saffron & 5% Niacinamide Radiance Serum",
        "category": "Skincare",
        "description": "Lightweight daytime serum blending real Kashmiri saffron stigma extract with niacinamide and alpha arbutin. Fades stubborn dark spots, acne hyperpigmentation, and sun tanning.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": f"{GCS_IMAGE_BASE_URL}/kashmiri_saffron_serum.jpg",
        "order": 3,
    },
    {
        "id": "bengal-linen-shirt",
        "name": "Bengal Breeze 100% Breathable Linen Shirt",
        "category": "Fashion",
        "description": "Relaxed-fit Cuban collar casual shirt woven from pure European flax linen. Ultra-breathable, moisture-wicking fabric designed specifically for hot and humid tropical summers.",
        "market": "Bangladesh",
        "language": "en",
        "image_url": f"{GCS_IMAGE_BASE_URL}/bengal_linen_shirt.jpg",
        "order": 4,
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
    If Firestore is empty or unreachable, returns core fallback products.
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
        print(f"Notice: Firestore demo_products lookup fell back to presets: {e}")

    # Fallback to core products if Firestore is unseeded or offline
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
