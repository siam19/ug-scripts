"""
Sprint 7 Phase 5c Offline Claim Verification Evaluator.

Loads saved evaluation outputs (results.jsonl), extracts every factual product claim
from each script's lines, and verifies each claim against the product's `facts` list
(supporting both dict Fact objects and plain strings).

Supports:
- `--mock`: Deterministic heuristic/mock claim extractor & verifier for offline testing.
- Live mode (default): Vertex AI Gemini structured verification via the `google-genai` SDK.

Usage:
    python -m evals.claim_check --mock
    python -m evals.claim_check --input apps/api/evals/results/phase5_ugc/results.jsonl
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Literal, Sequence

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Ensure apps/api is in sys.path whether run from repo root or apps/api
api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from prompts import format_facts_text  # noqa: E402
from schemas import Fact  # noqa: E402

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_INPUT_PATH = Path(__file__).resolve().parent / "results" / "phase5_ugc" / "results.jsonl"
DEFAULT_REPORT_FILENAME = "claim_check_report.md"

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bilingual keyword/unit equivalents for deterministic offline mock matching
BILINGUAL_SYNONYMS: dict[str, set[str]] = {
    "গ্রাম": {"gram", "grams", "g", "gm"},
    "gram": {"গ্রাম", "g", "gm"},
    "g": {"গ্রাম", "gram", "grams", "gm"},
    "লিটার": {"liter", "liters", "litre", "litres", "l"},
    "liter": {"লিটার", "l"},
    "l": {"লিটার", "liter", "liters"},
    "মিলি": {"ml", "milliliter", "milliliters"},
    "ml": {"মিলি"},
    "বছর": {"year", "years"},
    "year": {"বছর", "years"},
    "years": {"বছর", "year"},
    "সেকেন্ড": {"second", "seconds", "sec"},
    "second": {"সেকেন্ড", "seconds", "sec"},
    "seconds": {"সেকেন্ড", "second", "sec"},
    "মিনিট": {"minute", "minutes", "min"},
    "minutes": {"মিনিট", "minute", "min"},
    "ঘণ্টা": {"hour", "hours", "hr"},
    "hour": {"ঘণ্টা", "hours", "hr"},
    "hours": {"ঘণ্টা", "hour", "hr"},
    "ভোল্ট": {"volt", "volts", "v"},
    "volt": {"ভোল্ট", "v"},
    "v": {"ভোল্ট", "volt", "volts"},
    "গ্যারান্টি": {"guarantee", "warranty"},
    "guarantee": {"গ্যারান্টি", "warranty"},
    "warranty": {"গ্যারান্টি", "guarantee"},
    "ওয়ারেন্টি": {"warranty", "guarantee"},
    "স্ট্যাবিলাইজার": {"stabilizer"},
    "স্টেবিলাইজার": {"stabilizer"},
    "stabilizer": {"স্ট্যাবিলাইজার", "স্টেবিলাইজার"},
    "ইনভার্টার": {"inverter"},
    "inverter": {"ইনভার্টার"},
    "টেম্পার্ড": {"tempered"},
    "tempered": {"টেম্পার্ড"},
    "গ্লাস": {"glass"},
    "glass": {"গ্লাস"},
    "সিলভার": {"silver"},
    "silver": {"সিলভার"},
    "ক্লিন": {"clean"},
    "clean": {"ক্লিন"},
    "কম্প্রেসর": {"compressor"},
    "কম্প্রেসরের": {"compressor"},
    "কম্প্রেসারে": {"compressor"},
    "compressor": {"কম্প্রেসর"},
    "এলাচ": {"cardamom"},
    "cardamom": {"এলাচ"},
    "দারুচিনি": {"cinnamon"},
    "cinnamon": {"দারুচিনি"},
    "লবঙ্গ": {"clove"},
    "clove": {"লবঙ্গ"},
    "জিরা": {"cumin"},
    "cumin": {"জিরা"},
    "আদা": {"ginger"},
    "ginger": {"আদা"},
    "জয়ত্রী": {"mace"},
    "mace": {"জয়ত্রী"},
    "জয়ফল": {"nutmeg"},
    "nutmeg": {"জয়ফল"},
    "মরিচ": {"chilli", "chili"},
    "chilli": {"মরিচ"},
    "রসুন": {"garlic"},
    "garlic": {"রসুন"},
    "ধনে": {"coriander"},
    "coriander": {"ধনে"},
    "গোলমরিচ": {"pepper"},
    "pepper": {"গোলমরিচ"},
    "চিকেন": {"chicken"},
    "chicken": {"চিকেন"},
    "মাটন": {"mutton"},
    "mutton": {"মাটন"},
    "বিফ": {"beef"},
    "beef": {"বিফ"},
    "বিরিয়ানি": {"biryani"},
    "biryani": {"বিরিয়ানি"},
    "মশলা": {"masala", "spice", "spices"},
    "মসলা": {"masala", "spice", "spices"},
    "masala": {"মশলা", "মসলা", "spice"},
    "spice": {"মশলা", "মসলা", "masala"},
    "অ্যারোমা-লক": {"aroma-lock", "aroma", "lock"},
    "ফয়েল": {"foil"},
    "foil": {"ফয়েল"},
    "চা": {"tea"},
    "tea": {"চা"},
    "আম": {"mango"},
    "আমের": {"mango"},
    "mango": {"আম", "আমের"},
    "টেট্রা": {"tetra"},
    "tetra": {"টেট্রা"},
    "হট-ফিল": {"hot-fill"},
    "অ্যাসেপ্টিক": {"aseptic"},
    "হাইড্রোক্সিপ্যাটাইট": {"hydroxyapatite", "hap"},
    "ডেন্টিন": {"dentine"},
    "ডেন্টিস্ট": {"dentist", "dentists"},
    "ডেন্টিস্টদের": {"dentist", "dentists"},
    "dentist": {"ডেন্টিস্ট", "ডেন্টিস্টদের", "dentists"},
    "dentists": {"ডেন্টিস্ট", "ডেন্টিস্টদের", "dentist"},
    "সেনসিটিভিটি": {"sensitivity"},
    "সয়াবিন": {"soyabean", "soybean"},
    "ভিটামিন": {"vitamin"},
    "vitamin": {"ভিটামিন"},
    "মেহগনি": {"mahogany"},
    "বিকাশ": {"bkash"},
    "রিমিনারেলাইজেশন": {"remineralization"},
    "রেটিং": {"rating"},
    "এনার্জি": {"energy"},
    "ভিজিট": {"visit"},
    "আয়রন": {"iron"},
    "ভিডিও": {"video"},
    "লেকচার": {"lecture", "lectures"},
    "ফ্ল্যাশকার্ড": {"flashcard", "flashcards"},
    "কুইজ": {"quiz", "quizzes"},
    "লাইফটাইম": {"lifetime"},
    "স্পোকেন": {"spoken"},
    "ইংলিশ": {"english"},
    "ইংরেজি": {"english"},
    "ওয়ারড্রোব": {"wardrobe"},
    "ওয়ারড্রোবে": {"wardrobe"},
    "ওয়ারড্রোবটি": {"wardrobe"},
    "ড্রয়ার": {"drawer", "drawers"},
    "ড্রয়ারের": {"drawer", "drawers"},
    "ড্রয়ারের": {"drawer", "drawers"},
    "পলিপ্রোপিলিন": {"polypropylene"},
    "ভার্জিন": {"virgin"},
    "সুয়েড": {"suede"},
    "লোফার": {"loafer", "loafers"},
    "ফুটবেড": {"footbed"},
    "কুশন": {"cushion", "cushioned"},
    "কিউআর": {"qr"},
    "ফিঙ্গারপ্রিন্ট": {"fingerprint"},
    "মোবাইল": {"mobile"},
    "বিদ্যুৎ": {"electricity", "utility"},
    "বিল": {"bill", "bills"},
    "ন্যানো-লোন": {"nano-loan", "loan"},
    "কটন": {"cotton"},
    "মেরুন": {"maroon"},
}

STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "and", "or",
    "this", "that", "these", "those", "it", "its", "your", "our", "you",
    "all", "just", "only", "very", "more", "most", "can", "will", "has",
    "have", "had", "as", "into", "over", "under", "without", "within",
    "এই", "এবং", "আর", "ও", "যে", "থেকে", "দিয়ে", "করে", "করা", "হয়",
    "আছে", "থাকবে", "থাকে", "হবে", "এর", "এক", "একটি", "মাত্র", "সব", "কোনো",
    "আপনার", "আমাদের", "জন্য", "সাথে", "নিয়ে", "মধ্যে", "খুব", "একদম",
}

FACTUAL_KEYWORDS_EN: tuple[str, ...] = (
    "contain", "contains", "made with", "made of", "formulated", "formula",
    "ingredient", "weight", "net", "gram", "liter", "litre", "ml", "oz",
    "guarantee", "warranty", "voltage", "volt", "watt", "energy", "rating",
    "clinically", "doctor", "dentist", "recommended", "certified", "tested",
    "proven", "100%", "pure", "organic", "natural", "free of", "zero",
    "lasts", "relief", "seconds", "minutes", "hours", "years", "days",
    "tempered", "stainless", "waterproof", "spf", "vitamin", "acid",
    "discount", "% off", "free shipping", "free delivery", "cure", "heals",
    "saves", "reduces", "prevents", "protects", "seals", "technology",
    "material", "capacity", "size", "pack", "pouch", "bottle", "box",
)

FACTUAL_KEYWORDS_BN: tuple[str, ...] = (
    "গ্রাম", "লিটার", "মিলি", "ওজন", "গ্যারান্টি", "ওয়ারেন্টি", "ভোল্ট",
    "টেকনোলজি", "প্রযুক্তি", "ফর্মুলা", "উপাদান", "মিশ্রণ", "মেশানো",
    "ব্লেন্ড", "তৈরি", "আছে", "পাচ্ছেন", "পাবেন", "রেটিং", "সেকেন্ড",
    "মিনিট", "ঘণ্টা", "বছর", "দিন", "ডেন্টিস্ট", "ডাক্তার", "সার্টিফায়েড",
    "ক্লিনিক্যালি", "ডিসকাউন্ট", "ছাড়", "ফ্রি", "টেম্পার্ড", "স্ট্যাবিলাইজার",
    "স্টেবিলাইজার", "অ্যারোমা-লক", "সিলভার ক্লিন", "ইনভার্টার", "টেট্রা",
    "হট-ফিল", "অ্যাসেপ্টিক", "হাইড্রোক্সিপ্যাটাইট", "ডেন্টিন", "সুরক্ষা",
    "প্রতিরোধ", "ভিটামিন", "ফোর্টিফায়েড", "১০০%", "খাঁটি",
)

UNGROUNDED_RED_FLAGS: tuple[tuple[str, set[str]], ...] = (
    ("clinically proven", {"clinically", "clinical", "proven"}),
    ("doctor recommended", {"doctor", "doctors", "dermatologist"}),
    ("dentist recommended", {"dentist", "dentists", "ডেন্টিস্ট", "ডেন্টিস্টদের"}),
    ("no. 1", {"no. 1", "no.1", "#1", "number 1"}),
    ("#1", {"no. 1", "no.1", "#1", "number 1"}),
    ("free shipping", {"free shipping", "free delivery"}),
    ("free delivery", {"free shipping", "free delivery"}),
    ("discount", {"discount", "% off", "ছাড়", "ডিসকাউন্ট"}),
    ("% off", {"discount", "% off", "ছাড়", "ডিসকাউন্ট"}),
    ("50% off", {"50%"}),
    ("money-back", {"money-back", "refund"}),
    ("cure", {"cure", "cures"}),
)


class ClaimVerdict(BaseModel):
    """Verification verdict for a single factual product claim extracted from a script."""

    line_id: int = Field(..., description="1-based script line ID containing the claim")
    claim: str = Field(..., description="Concise statement of the factual product claim")
    verdict: Literal["supported", "unsupported", "contradicted"] = Field(
        ...,
        description=(
            "'supported' if directly backed by one or more product facts; "
            "'contradicted' if it conflicts with a product fact; "
            "'unsupported' if absent from or extrapolated beyond the facts"
        ),
    )
    matched_fact_ids: list[int] = Field(
        default_factory=list,
        description="1-based Fact IDs that support or contradict this claim",
    )
    rationale: str = Field(
        default="",
        description="Brief explanation of why the claim is supported, unsupported, or contradicted",
    )


class ScriptClaimCheckResult(BaseModel):
    """Structured Gemini output containing all factual claims verified in a script."""

    claims: list[ClaimVerdict] = Field(
        default_factory=list,
        description="All factual product claims extracted from the script lines and their verdicts",
    )


CLAIM_CHECK_PROMPT = """You are a strict fact-checking auditor evaluating an advertisement script against verified product facts.

PRODUCT: {product_name} ({category}, market: {market}, script language: {language})

{facts_block}

SCRIPT LINES (segment: {segment_name}):
{script_lines_block}

INSTRUCTIONS:
1. Read every spoken line in the script above.
2. Extract EVERY concrete factual product claim made about the product (for example: weight/volume/size, ingredients/materials, numeric performance claims, duration/speed claims, warranties/guarantees, certifications, rankings like "#1", technical features, packaging attributes, pricing/discounts, or specific functional/medical benefits).
3. Ignore purely emotional/relatable hooks, situational storytelling, rhetorical questions without product claims, and generic calls to action (e.g., "Order today from your nearest shop").
4. For each extracted factual claim, assign one verdict strictly against the VERIFIED PRODUCT FACTS above:
   - "supported": The claim is directly stated in or reasonably entailed by one or more facts (even if translated into {language}). Cite the matching Fact ID(s) in `matched_fact_ids`.
   - "contradicted": The claim directly conflicts with a fact (for example, a wrong number, weight, duration, or opposite attribute). Cite the conflicting Fact ID(s) in `matched_fact_ids`.
   - "unsupported": The claim introduces specs, numbers, guarantees, time-to-prepare estimates, ingredients, awards, or benefits not present in the facts (or extrapolates beyond them). Leave `matched_fact_ids` empty unless partially related.
5. Keep `claim` concise (in English) and provide a brief `rationale`. If the script contains no factual product claims, return an empty `claims` list.
"""


def normalize_facts(raw_facts: Sequence[Any] | None) -> list[Fact]:
    """Normalizes a product's facts list (supporting dict Fact objects, Fact models, and plain strings)."""
    if not raw_facts:
        return []

    normalized: list[Fact] = []
    for idx, item in enumerate(raw_facts):
        if isinstance(item, Fact):
            if item.text.strip():
                normalized.append(item)
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            raw_id = item.get("id")
            fact_id = int(raw_id) if isinstance(raw_id, int) or (isinstance(raw_id, str) and raw_id.isdigit()) else idx + 1
            raw_val = item.get("value", "core")
            value: Literal["core", "visual", "trivia"] = raw_val if raw_val in ("core", "visual", "trivia") else "core"
            normalized.append(Fact(id=fact_id, text=text, value=value))
        elif isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(Fact(id=idx + 1, text=text, value="core"))
    return normalized


def load_results_jsonl(path: Path) -> list[dict[str, Any]]:
    """Loads evaluation records from a results.jsonl file."""
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")

    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_num} of {path}: {exc}") from exc
    return records


def _normalize_digits(text: str) -> str:
    return text.translate(BENGALI_DIGITS)


def _tokenize_expanded(text: str) -> set[str]:
    """Tokenizes text (lowercase, normalized digits) and expands with bilingual synonyms."""
    normalized = _normalize_digits(text).lower()
    raw_tokens = re.findall(r"[\w\u0980-\u09ff]+(?:-[\w\u0980-\u09ff]+)*", normalized)
    tokens: set[str] = set()
    for tok in raw_tokens:
        if tok in STOPWORDS or (len(tok) <= 1 and not tok.isdigit()):
            continue
        tokens.add(tok)
        # Split alphanumeric tokens like '85v', '40g', '70টি' into number + suffix
        num_split = re.match(r"^(\d+(?:\.\d+)?)([^\d]+)$", tok)
        if num_split:
            num_part, suffix_part = num_split.groups()
            tokens.add(num_part)
            if len(suffix_part) >= 1 and suffix_part not in STOPWORDS:
                tokens.add(suffix_part)
                for syn in BILINGUAL_SYNONYMS.get(suffix_part, ()):
                    tokens.add(syn)
        # Also add sub-parts of hyphenated tokens (e.g. 'aroma-lock', '85v-300v')
        if "-" in tok:
            for part in tok.split("-"):
                if part and part not in STOPWORDS:
                    tokens.add(part)
                    part_split = re.match(r"^(\d+(?:\.\d+)?)([^\d]+)$", part)
                    if part_split:
                        tokens.add(part_split.group(1))
                        tokens.add(part_split.group(2))
        # Expand known bilingual synonyms
        for syn in BILINGUAL_SYNONYMS.get(tok, ()):
            tokens.add(syn)
    return tokens


def _extract_numbers_with_context(text: str) -> list[tuple[str, str]]:
    """Extracts (number, following_unit_or_token) pairs with Bengali digits normalized."""
    norm = _normalize_digits(text).lower()
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*(%|[\w\u0980-\u09ff]{1,12})?", norm)
    results: list[tuple[str, str]] = []
    for num, unit in matches:
        unit_clean = unit.strip()
        # Normalize common unit aliases
        if unit_clean in {"g", "gm", "gram", "grams", "গ্রাম", "গ্রামের"}:
            unit_norm = "gram"
        elif unit_clean in {"l", "liter", "liters", "litre", "litres", "লিটার", "লিটারের"}:
            unit_norm = "liter"
        elif unit_clean in {"ml", "milliliter", "milliliters", "মিলি", "মিলির"}:
            unit_norm = "ml"
        elif unit_clean in {"v", "volt", "volts", "ভোল্ট", "ভোল্টে", "ভোল্টেও"}:
            unit_norm = "volt"
        elif unit_clean in {"year", "years", "বছর", "বছরের"}:
            unit_norm = "year"
        elif unit_clean in {"sec", "second", "seconds", "সেকেন্ড", "সেকেন্ডের"}:
            unit_norm = "second"
        elif unit_clean in {"min", "minute", "minutes", "মিনিট", "মিনিটে"}:
            unit_norm = "minute"
        elif unit_clean in {"hr", "hour", "hours", "ঘণ্টা", "ঘন্টা"}:
            unit_norm = "hour"
        elif unit_clean == "%":
            unit_norm = "percent"
        else:
            unit_norm = unit_clean
        results.append((num, unit_norm))
    return results


def _has_factual_signal(clause: str) -> bool:
    """Heuristically determines whether a script clause asserts a factual product claim."""
    norm = _normalize_digits(clause).lower()
    if re.search(r"\d", norm):
        return True
    for kw in FACTUAL_KEYWORDS_EN:
        if kw in norm:
            return True
    for kw in FACTUAL_KEYWORDS_BN:
        if kw in norm:
            return True
    return False


def extract_claims_mock(lines: Sequence[dict[str, Any]]) -> list[tuple[int, str]]:
    """
    Deterministically extracts candidate factual product claims from script lines.
    Returns list of (line_id, claim_text).
    """
    claims: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        line_id = int(line.get("id", idx + 1))

        # Split line into sentence-level clauses
        raw_clauses = [c.strip() for c in re.split(r"[।.!?]+", text) if c.strip()]
        for clause in raw_clauses:
            if _has_factual_signal(clause):
                claims.append((line_id, clause))

    return claims


def verify_claim_mock(
    line_id: int,
    claim_text: str,
    facts: Sequence[Fact],
) -> ClaimVerdict:
    """
    Deterministically verifies a single claim against normalized product facts.
    """
    if not facts:
        return ClaimVerdict(
            line_id=line_id,
            claim=claim_text,
            verdict="unsupported",
            matched_fact_ids=[],
            rationale="No product facts provided to verify claim.",
        )

    claim_norm = _normalize_digits(claim_text).lower()
    claim_tokens = _tokenize_expanded(claim_text)
    claim_nums = _extract_numbers_with_context(claim_text)

    # Check red-flag ungrounded marketing/medical claims unless explicitly present in facts
    all_facts_norm = " ".join(_normalize_digits(f.text).lower() for f in facts)
    all_facts_tokens = set().union(*(_tokenize_expanded(f.text) for f in facts))
    for trigger, required_terms in UNGROUNDED_RED_FLAGS:
        if trigger in claim_norm:
            if not any(term in all_facts_norm or term in all_facts_tokens for term in required_terms):
                return ClaimVerdict(
                    line_id=line_id,
                    claim=claim_text,
                    verdict="unsupported",
                    matched_fact_ids=[],
                    rationale=f"Red-flag claim '{trigger}' is not present in verified facts.",
                )

    fact_nums_map: dict[int, list[tuple[str, str]]] = {
        f.id: _extract_numbers_with_context(f.text) for f in facts
    }
    fact_tokens_map: dict[int, set[str]] = {
        f.id: _tokenize_expanded(f.text) for f in facts
    }

    # Check numeric contradictions & numeric matches
    canonical_units = {"gram", "liter", "ml", "volt", "year", "second", "minute", "hour", "percent"}
    matched_fact_ids: list[int] = []
    contradicted_fact_ids: list[int] = []

    for c_num, c_unit in claim_nums:
        num_matched_anywhere = False
        for f in facts:
            f_nums = fact_nums_map[f.id]
            f_toks = fact_tokens_map[f.id]
            # Exact number match in this fact
            if any(fn == c_num for fn, _ in f_nums):
                num_matched_anywhere = True
                if f.id not in matched_fact_ids:
                    matched_fact_ids.append(f.id)
                continue

            # Check if same canonical unit exists in fact with a different number -> contradiction
            if c_unit in canonical_units:
                if any(fu == c_unit and fn != c_num for fn, fu in f_nums):
                    if f.id not in contradicted_fact_ids:
                        contradicted_fact_ids.append(f.id)
                elif c_unit in f_toks and f_nums:
                    if f.id not in contradicted_fact_ids:
                        contradicted_fact_ids.append(f.id)

        if contradicted_fact_ids and not num_matched_anywhere:
            return ClaimVerdict(
                line_id=line_id,
                claim=claim_text,
                verdict="contradicted",
                matched_fact_ids=contradicted_fact_ids,
                rationale=f"Numeric value '{c_num} {c_unit}' conflicts with fact(s) #{', #'.join(str(i) for i in contradicted_fact_ids)}.",
            )

        if not num_matched_anywhere:
            return ClaimVerdict(
                line_id=line_id,
                claim=claim_text,
                verdict="unsupported",
                matched_fact_ids=[],
                rationale=f"Numeric claim '{c_num}' not found in product facts.",
            )

    # Score semantic token overlap with each fact
    best_overlap = 0
    for f in facts:
        overlap = len(claim_tokens & fact_tokens_map[f.id])
        if overlap >= 2 or (overlap >= 1 and f.id in matched_fact_ids):
            if f.id not in matched_fact_ids:
                matched_fact_ids.append(f.id)
        if overlap > best_overlap:
            best_overlap = overlap

    if matched_fact_ids and best_overlap >= 1:
        return ClaimVerdict(
            line_id=line_id,
            claim=claim_text,
            verdict="supported",
            matched_fact_ids=matched_fact_ids,
            rationale=f"Matched fact(s) #{', #'.join(str(i) for i in matched_fact_ids)} via mock heuristic.",
        )

    return ClaimVerdict(
        line_id=line_id,
        claim=claim_text,
        verdict="unsupported",
        matched_fact_ids=[],
        rationale="Insufficient overlap with verified product facts.",
    )


def verify_script_mock(
    script: dict[str, Any],
    facts: Sequence[Fact],
) -> ScriptClaimCheckResult:
    """Runs deterministic mock claim extraction and verification on a single script."""
    lines = script.get("lines") or []
    extracted = extract_claims_mock(lines)
    verdicts = [verify_claim_mock(line_id, claim, facts) for line_id, claim in extracted]
    return ScriptClaimCheckResult(claims=verdicts)


def get_vertex_client() -> genai.Client:
    """Initializes a Vertex AI google-genai client from environment variables."""
    load_dotenv(api_dir / ".env")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT environment variable is not configured. "
            "Set Vertex AI credentials/env or pass --mock for offline heuristic verification."
        )
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    return genai.Client(vertexai=True, project=project, location=location)


def format_script_lines_for_prompt(lines: Sequence[dict[str, Any]]) -> str:
    """Formats script line dicts into numbered lines for Gemini verification."""
    formatted: list[str] = []
    for idx, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        lid = line.get("id", idx + 1)
        kind = line.get("kind", "concept")
        text = str(line.get("text", "")).strip()
        if text:
            formatted.append(f"{lid}. [{kind}] {text}")
    return "\n".join(formatted)


async def verify_script_gemini(
    client: genai.Client,
    model: str,
    record: dict[str, Any],
    script: dict[str, Any],
    facts: Sequence[Fact],
) -> tuple[ScriptClaimCheckResult, dict[str, int]]:
    """Calls Gemini on Vertex AI to extract and verify claims in a single script."""
    lines = script.get("lines") or []
    if not lines:
        return ScriptClaimCheckResult(claims=[]), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    facts_block = format_facts_text(facts) if facts else "- (No verified facts provided)"
    script_lines_block = format_script_lines_for_prompt(lines)
    if not script_lines_block:
        return ScriptClaimCheckResult(claims=[]), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    prompt = CLAIM_CHECK_PROMPT.format(
        product_name=record.get("product_name", record.get("product_id", "Unknown Product")),
        category=record.get("category", "General"),
        market=record.get("market", "Bangladesh"),
        language=record.get("language", "en"),
        facts_block=facts_block,
        segment_name=script.get("segment", "Unknown Segment"),
        script_lines_block=script_lines_block,
    )

    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ScriptClaimCheckResult,
            temperature=0.0,
        ),
    )

    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage["input_tokens"] = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        usage["output_tokens"] = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        usage["total_tokens"] = getattr(response.usage_metadata, "total_token_count", 0) or 0

    if getattr(response, "parsed", None) is not None:
        parsed = response.parsed
        if isinstance(parsed, ScriptClaimCheckResult):
            return parsed, usage
        return ScriptClaimCheckResult.model_validate(parsed), usage

    raw_text = getattr(response, "text", None) or "{}"
    return ScriptClaimCheckResult.model_validate_json(raw_text), usage


def aggregate_claim_metrics(product_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregates claim verification counts and percentages across all evaluated products."""
    total_products = len(product_results)
    total_scripts = 0
    clean_scripts = 0
    total_claims = 0
    supported = 0
    unsupported = 0
    contradicted = 0
    errors = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    for prod in product_results:
        usage = prod.get("usage", {})
        total_input_tokens += usage.get("input_tokens", 0)
        total_output_tokens += usage.get("output_tokens", 0)
        total_tokens += usage.get("total_tokens", 0)

        for script_res in prod.get("scripts", []):
            total_scripts += 1
            if script_res.get("error"):
                errors += 1
            claims = script_res.get("claims", [])
            script_ungrounded = 0
            for c in claims:
                total_claims += 1
                verdict = c.get("verdict")
                if verdict == "supported":
                    supported += 1
                elif verdict == "contradicted":
                    contradicted += 1
                    script_ungrounded += 1
                else:
                    unsupported += 1
                    script_ungrounded += 1
            if script_ungrounded == 0 and not script_res.get("error"):
                clean_scripts += 1

    ungrounded_total = unsupported + contradicted
    claim_denom = max(1, total_claims)
    script_denom = max(1, total_scripts)

    return {
        "products_evaluated": total_products,
        "total_scripts": total_scripts,
        "clean_scripts": clean_scripts,
        "clean_script_rate_pct": round((clean_scripts / script_denom) * 100, 1) if total_scripts else 100.0,
        "total_claims": total_claims,
        "supported_claims": supported,
        "supported_rate_pct": round((supported / claim_denom) * 100, 1) if total_claims else 100.0,
        "unsupported_claims": unsupported,
        "contradicted_claims": contradicted,
        "ungrounded_claims": ungrounded_total,
        "unsupported_claim_rate_pct": round((ungrounded_total / claim_denom) * 100, 1) if total_claims else 0.0,
        "errors": errors,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
    }


def generate_claim_report(
    input_label: str,
    mode: str,
    summary: dict[str, Any],
    product_results: list[dict[str, Any]],
) -> str:
    """Formats claim verification results as a Markdown report."""
    md = [
        "# Claim Verification Evaluation Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  ",
        f"**Input:** `{input_label}`  ",
        f"**Mode:** `{mode}`  ",
        f"**Products Evaluated:** {summary['products_evaluated']}  ",
        f"**Total Scripts Evaluated:** {summary['total_scripts']}  ",
        "",
        "## Summary Scorecard",
        "",
        "| Metric | Result |",
        "| :--- | :--- |",
        f"| **Total Factual Claims Extracted** | `{summary['total_claims']}` |",
        f"| **Supported Claims** | `{summary['supported_claims']}` (`{summary['supported_rate_pct']}%`) |",
        f"| **Unsupported Claims** (absent / extrapolated) | `{summary['unsupported_claims']}` |",
        f"| **Contradicted Claims** (conflicts with facts) | `{summary['contradicted_claims']}` |",
        f"| **Total Ungrounded Claim Rate** | `{summary['unsupported_claim_rate_pct']}%` ({summary['ungrounded_claims']}/{summary['total_claims']}) |",
        f"| **Clean Scripts (0 Ungrounded Claims)** | `{summary['clean_scripts']}/{summary['total_scripts']}` (`{summary['clean_script_rate_pct']}%`) |",
    ]

    if summary["total_tokens"] > 0:
        md.append(f"| **Verification Tokens Used** | `{summary['total_tokens']}` |")
    if summary["errors"] > 0:
        md.append(f"| **Script Verification Errors** | `{summary['errors']}` |")

    md.extend([
        "",
        "## Per-Product Breakdown",
        "",
        "| Product | Lang | Facts | Scripts | Claims | Supported | Unsupported | Contradicted | Ungrounded % | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])

    flagged_entries: list[dict[str, Any]] = []

    for prod in product_results:
        p_claims = 0
        p_sup = 0
        p_unsup = 0
        p_contra = 0
        p_err = 0

        for s_res in prod.get("scripts", []):
            if s_res.get("error"):
                p_err += 1
            for c in s_res.get("claims", []):
                p_claims += 1
                verdict = c.get("verdict")
                if verdict == "supported":
                    p_sup += 1
                elif verdict == "contradicted":
                    p_contra += 1
                    flagged_entries.append({
                        "product_name": prod["product_name"],
                        "segment": s_res["segment"],
                        **c,
                    })
                else:
                    p_unsup += 1
                    flagged_entries.append({
                        "product_name": prod["product_name"],
                        "segment": s_res["segment"],
                        **c,
                    })

        p_ungrounded = p_unsup + p_contra
        p_rate = round((p_ungrounded / p_claims) * 100, 1) if p_claims else 0.0
        status_icon = "✅" if (p_ungrounded == 0 and p_err == 0) else "⚠️"
        p_name = prod["product_name"][:32] + ("..." if len(prod["product_name"]) > 32 else "")

        md.append(
            f"| {p_name} | {prod['language']} | {prod['fact_count']} | {len(prod['scripts'])} | "
            f"{p_claims} | {p_sup} | {p_unsup} | {p_contra} | {p_rate}% | {status_icon} |"
        )

    md.extend([
        "",
        "## Flagged Claims (Unsupported or Contradicted)",
        "",
    ])

    if not flagged_entries:
        md.append("No unsupported or contradicted claims were flagged.")
    else:
        for idx, entry in enumerate(flagged_entries, start=1):
            fact_refs = ", ".join(f"#{fid}" for fid in entry.get("matched_fact_ids", [])) or "none"
            md.append(
                f"{idx}. **[{entry['verdict'].upper()}]** `{entry['product_name']}` — *{entry['segment']}* "
                f"(Line {entry['line_id']}): {entry['claim']}  "
            )
            md.append(f"   - Related Fact IDs: `{fact_refs}` | Rationale: {entry.get('rationale', '')}")

    md.extend([
        "",
        "---",
        "*Report generated by `apps/api/evals/claim_check.py`.*",
    ])
    return "\n".join(md)


async def run_claim_check(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path | None = None,
    mock: bool = False,
    limit: int | None = None,
    model: str | None = None,
    client: genai.Client | None = None,
    json_out_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Runs offline claim verification across all records in a results.jsonl file."""
    records = load_results_jsonl(input_path)
    if limit is not None:
        records = records[:limit]

    resolved_output = output_path or (input_path.parent / DEFAULT_REPORT_FILENAME)
    resolved_model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    mode_label = "mock (offline heuristic)" if mock else f"live ({resolved_model})"

    active_client = None if mock else (client or get_vertex_client())
    semaphore = asyncio.Semaphore(5)

    product_results: list[dict[str, Any]] = []

    for rec in records:
        facts = normalize_facts(rec.get("facts"))
        scripts = rec.get("scripts") or []
        prod_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        script_results: list[dict[str, Any]] = []

        if mock:
            for script in scripts:
                res = verify_script_mock(script, facts)
                script_results.append({
                    "segment": script.get("segment", "Unknown Segment"),
                    "claims": [c.model_dump() for c in res.claims],
                })
        else:
            async def _check_one(s: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
                async with semaphore:
                    try:
                        assert active_client is not None
                        res, usage = await verify_script_gemini(
                            client=active_client,
                            model=resolved_model,
                            record=rec,
                            script=s,
                            facts=facts,
                        )
                        return {
                            "segment": s.get("segment", "Unknown Segment"),
                            "claims": [c.model_dump() for c in res.claims],
                        }, usage
                    except Exception as exc:
                        return {
                            "segment": s.get("segment", "Unknown Segment"),
                            "claims": [],
                            "error": str(exc),
                        }, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

            pairs = await asyncio.gather(*(_check_one(s) for s in scripts))
            for s_res, s_usage in pairs:
                script_results.append(s_res)
                prod_usage["input_tokens"] += s_usage["input_tokens"]
                prod_usage["output_tokens"] += s_usage["output_tokens"]
                prod_usage["total_tokens"] += s_usage["total_tokens"]

        product_results.append({
            "product_id": rec.get("product_id", rec.get("product_name", "unknown")),
            "product_name": rec.get("product_name", rec.get("product_id", "Unknown Product")),
            "language": rec.get("language", "en"),
            "format": rec.get("format", "ugc"),
            "fact_count": len(facts),
            "usage": prod_usage,
            "scripts": script_results,
        })

    summary = aggregate_claim_metrics(product_results)

    try:
        display_input = str(input_path.relative_to(api_dir.parent.parent))
    except ValueError:
        display_input = input_path.name

    report_md = generate_claim_report(
        input_label=display_input,
        mode=mode_label,
        summary=summary,
        product_results=product_results,
    )
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(report_md, encoding="utf-8")

    if json_out_path is not None:
        json_out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_out_path, "w", encoding="utf-8") as jf:
            for item in product_results:
                jf.write(json.dumps(item, ensure_ascii=False) + "\n")

    return summary, product_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprint 7 Phase 5c Offline Claim Verification Evaluator")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to results.jsonl (default: apps/api/evals/results/phase5_ugc/results.jsonl)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to output markdown report (default: <input_dir>/claim_check_report.md)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run deterministic offline heuristic verifier instead of live Vertex AI Gemini",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of products to evaluate",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Override Gemini model for live mode (default: $GEMINI_MODEL or {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write detailed claim verdicts as JSONL",
    )

    args = parser.parse_args()
    summary, _ = asyncio.run(
        run_claim_check(
            input_path=args.input,
            output_path=args.output,
            mock=args.mock,
            limit=args.limit,
            model=args.model,
            json_out_path=args.json_out,
        )
    )
    resolved_output = args.output or (args.input.parent / DEFAULT_REPORT_FILENAME)
    print(f"Claim check complete ({'mock' if args.mock else 'live'}): "
          f"{summary['supported_claims']}/{summary['total_claims']} supported, "
          f"{summary['ungrounded_claims']} ungrounded ({summary['unsupported_claim_rate_pct']}%)")
    print(f"Report written to: {resolved_output}")


if __name__ == "__main__":
    main()
