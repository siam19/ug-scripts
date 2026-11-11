"""
Sprint 4 Evaluation Harness Runner.

Usage:
    python -m apps.api.evals.run --label baseline
    python -m apps.api.evals.run --label baseline --mock
    python -m apps.api.evals.run --label baseline --language bn --limit 2
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

# Ensure apps/api is in sys.path
api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from google.genai import types
from schemas import Line, Reason, Script, Segment, Segments
from usage import start_token_tracking
from main import run_stage1, run_stage2
from evals.metrics import aggregate_run_metrics, evaluate_script


def load_product_fixtures(product_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Loads all product JSON files from the fixtures directory."""
    fixtures: list[dict[str, Any]] = []
    files = sorted(product_dir.glob("*.json"))
    if limit:
        files = files[:limit]
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            fixtures.append(data)
    return fixtures


def create_mock_stage1_response(product: dict[str, Any]) -> Segments:
    """Generates a realistic mock Segments object for offline dry-runs."""
    return Segments(
        product_facts=[
            f"Authentic {product['name']}",
            f"Formulated and tested for {product.get('market', 'Bangladesh')}",
            "100% genuine guaranteed ingredients and craftsmanship",
            "Convenient lightweight daily packaging",
            "Designed for heat, humidity, and active daily commuting",
        ],
        segments=[
            Segment(
                name="Busy City Professionals",
                who="24-35 year olds working long hours in urban hubs",
                pain_point="Daily fatigue and lack of time for complicated routines",
                platforms=["TikTok", "Reels"],
            ),
            Segment(
                name="Value Conscious Students",
                who="18-24 year old college and university students",
                pain_point="Looking for premium quality without overspending",
                platforms=["Instagram", "TikTok"],
            ),
            Segment(
                name="Health & Wellness Conscious",
                who="28-45 year olds prioritizing clean and reliable essentials",
                pain_point="Tired of misleading claims and synthetic additives",
                platforms=["Facebook", "YouTube Shorts"],
            ),
        ],
    )


def create_mock_stage2_response(segment_name: str, language: str) -> Script:
    """Generates a realistic mock Script object for offline dry-runs (around 65-75 words)."""
    if language == "bn":
        lines = [
            Line(id=1, kind="hook", text="প্রতিদিন অফিস শেষে শরীর অসম্ভব ক্লান্ত লাগছে?"),
            Line(id=2, kind="concept", text="ঢাকার এই অসহ্য গরম আর জ্যামে সারাদিন কাজ করার পর এমন ক্লান্তি খুব স্বাভাবিক।"),
            Line(id=3, kind="concept", text="এই বিশেষ প্রাকৃতিক ফর্মুলা ক্লান্তি দূর করে ত্বকের ন্যাচারাল ব্যালান্স ফিরিয়ে আনে খুব দ্রুত।"),
            Line(id=4, kind="concept", text="কোন রকম ক্ষতিকর কেমিক্যাল বা চিটচিটে ভাব ছাড়া এটা দিনে দুইবার ব্যবহার করলেই পার্থক্য বুঝতে পারবেন।"),
            Line(id=5, kind="concept", text="মাত্র তিন সপ্তাহের নিয়মিত ব্যবহারে নিজের এনার্জি আর রিফ্রেশিং অনুভূতি চোখে পড়ার মতো বদলে যাবে।"),
            Line(id=6, kind="cta", text="দেরি না করে নিজের বোতলটি পেতে এখনই নিচের লিংকে ট্যাপ করুন।"),
        ]
        reasons = [
            Reason(
                title="Direct Relatable Hook",
                why="Calls out after-work exhaustion immediately in conversational Bengali.",
                line_ids=[1],
            ),
            Reason(
                title="Benefit and Mechanism",
                why="Explains rapid natural absorption without greasy residue.",
                line_ids=[3, 4],
            ),
            Reason(
                title="Low Friction CTA",
                why="Guides viewer to tap the order link directly.",
                line_ids=[6],
            ),
        ]
    else:
        lines = [
            Line(id=1, kind="hook", text="If your energy crashes every single afternoon, listen up."),
            Line(id=2, kind="concept", text="Running from meetings to errands in the humid weather completely drains your focus."),
            Line(id=3, kind="concept", text="This lightweight formula was specifically engineered to restore sustained vitality without jitters."),
            Line(id=4, kind="concept", text="It absorbs cleanly within thirty seconds, leaving zero sticky residue behind on your skin."),
            Line(id=5, kind="concept", text="In just three weeks of daily morning use, you notice consistent stamina all afternoon."),
            Line(id=6, kind="cta", text="Tap the link below right now to get yours delivered to your doorstep."),
        ]
        reasons = [
            Reason(
                title="Curiosity Problem Hook",
                why="Stops the scroll by calling out afternoon energy crashes.",
                line_ids=[1],
            ),
            Reason(
                title="Sensory Proof and Absorption",
                why="Reassures the viewer about quick 30-second absorption and zero residue.",
                line_ids=[3, 4],
            ),
            Reason(
                title="Direct Frictionless CTA",
                why="Clear doorstep delivery call to action.",
                line_ids=[6],
            ),
        ]

    return Script(
        segment=segment_name,
        lines=lines,
        reasons=reasons,
    )

    return Script(
        segment=segment_name,
        lines=lines,
        reasons=reasons,
    )


async def evaluate_single_product(
    product: dict[str, Any],
    sample_png_bytes: bytes,
    target_language: str,
    format_type: str = "ugc",
    mock: bool = False,
    fixtures_dir: Path | None = None,
) -> dict[str, Any]:
    """Runs Stage 1 and Stage 2 for a single product and evaluates output."""
    acc = start_token_tracking()
    t_start = time.perf_counter()

    name = product["name"]
    category = product.get("category", "General")
    description = product.get("description", "")
    market = product.get("market", "Bangladesh")
    lang = target_language or product.get("default_language", "en")

    # Resolve accompanying product image
    img_part = None
    if fixtures_dir and product.get("image_filename"):
        img_path = fixtures_dir / "images" / product["image_filename"]
        if img_path.exists():
            img_bytes = img_path.read_bytes()
            suffix = img_path.suffix.lower()
            if suffix == ".webp":
                mime_type = "image/webp"
            elif suffix in (".jpg", ".jpeg"):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"
            img_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)

    if img_part is None:
        img_part = types.Part.from_bytes(data=sample_png_bytes, mime_type="image/png")

    if mock:
        t_stage1_start = time.perf_counter()
        await asyncio.sleep(0.05)  # simulate latency
        segs = create_mock_stage1_response(product)
        t_stage1_end = time.perf_counter()

        t_stage2_start = time.perf_counter()
        await asyncio.sleep(0.08)
        scripts = [
            create_mock_stage2_response(s.name, lang)
            for s in segs.segments
        ]
        t_stage2_end = time.perf_counter()
        # Add mock token usage
        acc.add(450, 220, 670, stage="extract")
        acc.add(1200, 580, 1780, stage="script")
    else:
        # Real invocation
        t_stage1_start = time.perf_counter()
        segs = await run_stage1(
            name=name,
            category=category,
            description=description,
            market=market,
            parts=[img_part],
        )
        t_stage1_end = time.perf_counter()

        t_stage2_start = time.perf_counter()
        scripts = await run_stage2(
            name=name,
            category=category,
            market=market,
            language=lang,
            facts=segs.product_facts,
            segments=segs.segments,
            angles=segs.angles,
        )
        t_stage2_end = time.perf_counter()

    t_end = time.perf_counter()

    stage1_sec = round(t_stage1_end - t_stage1_start, 2)
    stage2_sec = round(t_stage2_end - t_stage2_start, 2)
    total_sec = round(t_end - t_start, 2)

    # Evaluate each script
    script_evals = [
        evaluate_script(script, language=lang, format_type=format_type)
        for script in scripts
    ]

    return {
        "product_id": product.get("id", name),
        "product_name": name,
        "category": category,
        "market": market,
        "language": lang,
        "format": format_type,
        "timing": {
            "stage1_sec": stage1_sec,
            "stage2_sec": stage2_sec,
            "ttfc_sec": stage1_sec,  # In streaming, segments emit right after stage 1
            "total_sec": total_sec,
        },
        "usage": acc.to_dict(),
        "facts": [f.model_dump() if hasattr(f, "model_dump") else f for f in segs.product_facts],
        "angles": [a.model_dump() if hasattr(a, "model_dump") else a for a in getattr(segs, "angles", [])],
        "product_appearance": getattr(segs, "product_appearance", ""),
        "segments": [s.model_dump() for s in segs.segments],
        "scripts": [s.model_dump() for s in scripts],
        "script_evals": script_evals,
    }


def generate_markdown_report(label: str, summary: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Formats evaluation results as a clean Markdown report."""
    md = [
        f"# Evaluation Report: `{label}`",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  ",
        f"**Products Evaluated:** {summary['products_evaluated']}  ",
        f"**Total Scripts Generated:** {summary['total_scripts']}  ",
        "",
        "## Summary Scorecard",
        "",
        "| Metric | Result | Target Benchmark |",
        "| :--- | :--- | :--- |",
        f"| **Overall Hard Rules Pass Rate** | `{summary['overall_hard_pass_rate']}%` | >= 90% |",
        f"| **Structure Pass Rate** (Hook 1st, CTA Last, Valid Reasons) | `{summary['structure_pass_rate']}%` | >= 95% |",
        f"| **Word Count Range Pass Rate** | `{summary['word_range_pass_rate']}%` | >= 85% |",
        f"| **Hook Brevity Pass Rate** (<= 12 words) | `{summary['hook_length_pass_rate']}%` | >= 90% |",
        f"| **Banned Cliché Violations** | `{summary['total_banned_phrase_hits']}` hits ({summary['banned_hit_rate_pct']}%) | 0 hits |",
        f"| **Repetition Loop Violations** | `{summary.get('total_repetition_hits', 0)}` hits ({summary.get('repetition_hit_rate_pct', 0.0)}%) | 0 hits |",
        f"| **Bengali Script Ratio** (Bangla scripts) | `{summary['avg_bengali_script_ratio']}` | >= 0.85 |",
        f"| **Average Script Word Count** | `{summary['avg_words_per_script']}` words | 60 - 90 words |",
        f"| **Average Hook Word Count** | `{summary['avg_hook_words']}` words | <= 10 words |",
        f"| **Average TTFC** (Time to First Content) | `{summary['avg_ttfc_sec']}s` | <= 4.5s |",
        f"| **Average Total Pipeline Latency** | `{summary['avg_total_latency_sec']}s` | <= 8.0s |",
        f"| **Average Tokens per Product** | `{summary['avg_tokens_per_product']}` tokens | - |",
        "",
        "## Per-Product Breakdown",
        "",
        "| Product | Lang | Words (Min/Avg/Max) | Hook Brevity | Banned Hits | Stage 1 (s) | Total (s) | Pass? |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for item in items:
        words = [se["total_words"] for se in item["script_evals"]]
        w_min = min(words) if words else 0
        w_max = max(words) if words else 0
        w_avg = round(sum(words) / max(1, len(words)), 1)
        
        hooks = [se["hook_words"] for se in item["script_evals"]]
        h_avg = round(sum(hooks) / max(1, len(hooks)), 1)
        
        banned = sum(len(se["banned_hits"]) for se in item["script_evals"])
        all_pass = all(se["all_hard_rules_pass"] for se in item["script_evals"])
        status_icon = "✅" if all_pass else "⚠️"
        
        p_name = item["product_name"][:28] + ("..." if len(item["product_name"]) > 28 else "")
        timing = item["timing"]
        
        md.append(
            f"| {p_name} | {item['language']} | {w_min}/{w_avg}/{w_max} | {h_avg} words | {banned} | {timing['stage1_sec']}s | {timing['total_sec']}s | {status_icon} |"
        )

    md.extend([
        "",
        "---",
        "*Report generated automatically by `apps/api/evals/run.py`.*",
    ])
    return "\n".join(md)


async def run_harness(
    label: str,
    format_type: str = "ugc",
    language_filter: str = "all",
    limit: int | None = None,
    mock: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Executes the evaluation runner across loaded product fixtures."""
    fixtures_dir = Path(__file__).resolve().parent / "products"
    products = load_product_fixtures(fixtures_dir, limit=limit)

    sample_png_path = fixtures_dir / "sample.png"
    if sample_png_path.exists():
        sample_png_bytes = sample_png_path.read_bytes()
    else:
        sample_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\xdacd\xf8\xcfP\x0f\x00\x03\x86\x01\x80Z4}k\x00\x00\x00\x00IEND\xaeB`\x82"

    eval_records: list[dict[str, Any]] = []

    print(f"\n🚀 Running Eval Harness: label='{label}' (format={format_type}, mock={mock})")
    print(f"Loaded {len(products)} fixture products.\n" + "-" * 60)

    for i, prod in enumerate(products, 1):
        target_lang = prod.get("default_language", "en")
        if language_filter != "all" and target_lang != language_filter:
            continue

        print(f"[{i}/{len(products)}] Evaluating: {prod['name']} ({target_lang})...", end="", flush=True)
        try:
            record = await evaluate_single_product(
                product=prod,
                sample_png_bytes=sample_png_bytes,
                target_language=target_lang,
                format_type=format_type,
                mock=mock,
                fixtures_dir=fixtures_dir,
            )
            eval_records.append(record)
            all_passed = all(se["all_hard_rules_pass"] for se in record["script_evals"])
            print(f" {'✅ Passed' if all_passed else '⚠️ Issues'} ({record['timing']['total_sec']}s)")
        except Exception as e:
            print(f" ❌ ERROR: {e}")

    summary = aggregate_run_metrics(eval_records)

    # Output directory
    results_dir = Path(__file__).resolve().parent / "results" / label
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write results.jsonl
    jsonl_path = results_dir / "results.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for rec in eval_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2. Write report.md
    report_content = generate_markdown_report(label, summary, eval_records)
    report_path = results_dir / "report.md"
    report_path.write_text(report_content, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"📊 EVALUATION SUMMARY: `{label}`")
    print("=" * 60)
    print(f"Products Evaluated:         {summary['products_evaluated']}")
    print(f"Total Scripts:              {summary['total_scripts']}")
    print(f"Overall Hard Pass Rate:     {summary['overall_hard_pass_rate']}%")
    print(f"Structure Pass Rate:        {summary['structure_pass_rate']}%")
    print(f"Word Range Pass Rate:       {summary['word_range_pass_rate']}%")
    print(f"Avg Words / Script:         {summary['avg_words_per_script']}")
    print(f"Avg Hook Words:             {summary['avg_hook_words']}")
    print(f"Banned Phrase Hits:         {summary['total_banned_phrase_hits']}")
    print(f"Repetition Loop Hits:       {summary.get('total_repetition_hits', 0)}")
    print(f"Avg Bengali Script Ratio:   {summary['avg_bengali_script_ratio']}")
    print(f"Avg TTFC:                   {summary['avg_ttfc_sec']}s")
    print(f"Avg Total Latency:          {summary['avg_total_latency_sec']}s")
    print(f"Total Tokens Consumed:      {summary['total_tokens_consumed']}")
    print("=" * 60)
    print(f"📄 Detailed Report Saved: {report_path}")
    print(f"💾 Raw JSONL Data Saved:  {jsonl_path}\n")

    return summary, eval_records


def main():
    parser = argparse.ArgumentParser(description="Sprint 4 Eval Harness Runner")
    parser.add_argument("--label", type=str, default="baseline", help="Identifier for evaluation run")
    parser.add_argument("--format", type=str, default="ugc", choices=["ugc", "commercial_30s"], help="Script format")
    parser.add_argument("--language", type=str, default="all", choices=["all", "en", "bn"], help="Filter by language")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test products")
    parser.add_argument("--mock", action="store_true", help="Run with simulated responses (offline/test mode)")

    args = parser.parse_args()
    asyncio.run(
        run_harness(
            label=args.label,
            format_type=args.format,
            language_filter=args.language,
            limit=args.limit,
            mock=args.mock,
        )
    )


if __name__ == "__main__":
    main()
