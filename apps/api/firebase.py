"""
Firebase & Google Cloud Services Integration.

Provides lazy-initialized clients for:
1. Cloud Firestore (AsyncClient for FastAPI async routes).
2. Google Cloud Storage (for archiving images and fetching demo assets).
Includes mock overrides for offline pytest execution.
"""

import os
from typing import Any
from google.cloud import firestore, storage

# Sanitize dangling credentials path pointing to non-existent files
_cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if _cred_path and not os.path.exists(_cred_path):
    os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# Global singleton client caches
_firestore_client: firestore.AsyncClient | None = None
_storage_client: storage.Client | None = None
_mock_firestore: Any | None = None
_mock_storage: Any | None = None


def get_project_id() -> str:
    """Returns the configured GCP project ID."""
    return os.environ.get("GOOGLE_CLOUD_PROJECT", "ugstar")


def get_firestore_client() -> firestore.AsyncClient:
    """
    Returns an asynchronous Firestore client singleton.
    Returns mock client if configured (e.g. during automated test runs).
    """
    global _firestore_client, _mock_firestore
    if _mock_firestore is not None:
        return _mock_firestore

    if _firestore_client is None:
        project = get_project_id()
        database = os.environ.get("FIRESTORE_DATABASE", "(default)")
        _firestore_client = firestore.AsyncClient(project=project, database=database)
    return _firestore_client


def get_storage_client() -> storage.Client:
    """Returns a Google Cloud Storage client singleton."""
    global _storage_client, _mock_storage
    if _mock_storage is not None:
        return _mock_storage

    if _storage_client is None:
        project = get_project_id()
        _storage_client = storage.Client(project=project)
    return _storage_client


def get_storage_bucket_name() -> str:
    """Returns the default Firebase / GCS storage bucket name."""
    project = get_project_id()
    return os.environ.get(
        "FIREBASE_STORAGE_BUCKET",
        f"{project}.firebasestorage.app",
    )


def get_storage_bucket(bucket_name: str | None = None) -> storage.Bucket:
    """Returns the target Storage bucket."""
    client = get_storage_client()
    target_bucket = bucket_name or get_storage_bucket_name()
    return client.bucket(target_bucket)


# Test hooks for offline test suite isolation
def set_mock_firestore(mock: Any) -> None:
    global _mock_firestore
    _mock_firestore = mock


def set_mock_storage(mock: Any) -> None:
    global _mock_storage
    _mock_storage = mock


def reset_clients() -> None:
    global _firestore_client, _storage_client, _mock_firestore, _mock_storage
    _firestore_client = None
    _storage_client = None
    _mock_firestore = None
    _mock_storage = None
