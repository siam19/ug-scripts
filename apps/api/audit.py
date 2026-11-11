"""
Audit Logging and Media Archival Module.

Asynchronously logs all generation and regeneration requests to Firestore 'generation_logs'
and archives user-uploaded product images to Firebase/GCS Cloud Storage.
Updates cumulative token counters on 'access_codes' documents via firestore.Increment.
"""

import uuid
from typing import Any
from google.cloud import firestore

from firebase import get_firestore_client, get_storage_bucket
from auth import clear_auth_cache
from prompts import PIPELINE_VERSION, PROMPT_VERSIONS


async def log_generation_task(
    access_code: str,
    endpoint: str,
    product_meta: dict[str, Any],
    image_bytes: bytes | None = None,
    image_content_type: str | None = None,
    demo_image_url: str | None = None,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    usage: dict[str, int] | None = None,
) -> None:
    """
    Executes in a FastAPI BackgroundTask after response delivery:
    1. Uploads image_bytes to Storage at uploads/{access_code}/{log_id}.{ext} (if custom file).
    2. Writes generation metadata, payloads, and token consumption to 'generation_logs'.
    3. Atomically increments token usage on 'access_codes/{access_code}'.
    """
    try:
        log_id = str(uuid.uuid4())
        usage_data = usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        image_uri = demo_image_url or ""

        # 1. Archive uploaded image if present
        if image_bytes and len(image_bytes) > 0:
            ext = "webp"
            if image_content_type:
                if "jpeg" in image_content_type or "jpg" in image_content_type:
                    ext = "jpg"
                elif "png" in image_content_type:
                    ext = "png"
            try:
                bucket = get_storage_bucket()
                blob_path = f"uploads/{access_code}/{log_id}.{ext}"
                blob = bucket.blob(blob_path)
                blob.upload_from_string(
                    image_bytes,
                    content_type=image_content_type or "application/octet-stream",
                )
                image_uri = f"gs://{bucket.name}/{blob_path}"
            except Exception as upload_err:
                print(f"Warning: Failed to archive image to Storage: {upload_err}")

        # 2. Write generation audit log in Firestore
        db = get_firestore_client()
        log_ref = db.collection("generation_logs").document(log_id)
        await log_ref.set({
            "log_id": log_id,
            "access_code": access_code,
            "endpoint": endpoint,
            "product_meta": product_meta,
            "pipeline_version": PIPELINE_VERSION,
            "prompt_versions": PROMPT_VERSIONS,
            "image_storage_uri": image_uri,
            "request_payload": request_payload or {},
            "response_payload": response_payload or {},
            "usage": usage_data,
            "created_at": firestore.SERVER_TIMESTAMP,
        })

        # 3. Increment counters on access code (unless admin key)
        if access_code and access_code != "ADMIN":
            try:
                code_ref = db.collection("access_codes").document(access_code)
                await code_ref.update({
                    "total_input_tokens": firestore.Increment(usage_data.get("input_tokens", 0)),
                    "total_output_tokens": firestore.Increment(usage_data.get("output_tokens", 0)),
                    "total_tokens": firestore.Increment(usage_data.get("total_tokens", 0)),
                    "generation_count": firestore.Increment(1),
                    "last_used_at": firestore.SERVER_TIMESTAMP,
                })
                clear_auth_cache()
            except Exception as code_err:
                print(f"Warning: Failed to increment token counters on {access_code}: {code_err}")

    except Exception as e:
        print(f"Error in generation audit logging: {e}")
