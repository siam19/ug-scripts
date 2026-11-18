"""
CLI Script to Export Firestore 'script_feedback' Documents to JSONL.

Exports user ratings, constrained tags, comments, implicit quality signals,
and script snapshots for offline evaluation and few-shot curation.

Usage:
  cd apps/api
  .venv/bin/python scripts/export_feedback.py --output feedback_export.jsonl
  .venv/bin/python scripts/export_feedback.py --rating -1 --language bn --output negatives_bn.jsonl
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add apps/api to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from firebase import get_firestore_client


def _json_default(obj: Any) -> str:
    """Serializes Firestore timestamps / datetimes to ISO-8601 strings."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


async def fetch_feedback_records(
    *,
    rating: int | None = None,
    language: str | None = None,
    script_format: str | None = None,
    limit: int | None = None,
    db: Any = None,
) -> list[dict[str, Any]]:
    """Fetches and optionally filters documents from the Firestore `script_feedback` collection."""
    client = db or get_firestore_client()
    docs = await client.collection("script_feedback").get()

    records: list[dict[str, Any]] = []
    for doc in docs:
        data = doc.to_dict() or {}
        if "feedback_id" not in data and getattr(doc, "id", None):
            data["feedback_id"] = doc.id

        if rating is not None and data.get("rating") != rating:
            continue
        if language is not None and data.get("language") != language:
            continue
        if script_format is not None and data.get("script_format") != script_format:
            continue

        records.append(data)
        if limit is not None and len(records) >= limit:
            break

    return records


async def export_feedback_to_jsonl(
    output_path: Path | str | None = None,
    *,
    rating: int | None = None,
    language: str | None = None,
    script_format: str | None = None,
    limit: int | None = None,
    db: Any = None,
) -> list[dict[str, Any]]:
    """
    Exports `script_feedback` documents to a JSONL file (or stdout when output_path is '-' or None).
    Returns the exported list of records.
    """
    records = await fetch_feedback_records(
        rating=rating,
        language=language,
        script_format=script_format,
        limit=limit,
        db=db,
    )

    lines = [
        json.dumps(record, ensure_ascii=False, default=_json_default)
        for record in records
    ]

    if output_path is None or str(output_path) == "-":
        for line in lines:
            print(line)
    else:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = ("\n".join(lines) + "\n") if lines else ""
        target.write_text(payload, encoding="utf-8")

    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export Firestore script_feedback documents to JSONL."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="feedback_export.jsonl",
        help="Output JSONL file path, or '-' for stdout (default: feedback_export.jsonl)",
    )
    parser.add_argument(
        "--rating",
        type=int,
        choices=[-1, 1],
        default=None,
        help="Filter by rating (-1 or 1)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Filter by script language (e.g. 'en' or 'bn')",
    )
    parser.add_argument(
        "--format",
        dest="script_format",
        type=str,
        default=None,
        help="Filter by script_format (e.g. 'ugc' or 'commercial_30s')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of records to export",
    )
    args = parser.parse_args(argv)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "ugstar")
    if args.output != "-":
        print(f"Exporting script_feedback from Firestore project '{project_id}'...")

    records = asyncio.run(
        export_feedback_to_jsonl(
            args.output,
            rating=args.rating,
            language=args.language,
            script_format=args.script_format,
            limit=args.limit,
        )
    )

    if args.output != "-":
        print(f"Exported {len(records)} feedback record(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
