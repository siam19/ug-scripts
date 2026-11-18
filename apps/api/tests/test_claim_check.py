"""
Tests for Sprint 7 Phase 5c Offline Claim Verification Evaluator.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from evals.claim_check import (
    ClaimVerdict,
    ScriptClaimCheckResult,
    aggregate_claim_metrics,
    extract_claims_mock,
    get_vertex_client,
    load_results_jsonl,
    normalize_facts,
    run_claim_check,
    verify_script_mock,
)
from schemas import Fact


def test_normalize_facts_supports_dicts_strings_and_models():
    raw = [
        {"id": 10, "text": "Net weight is 40g.", "value": "core"},
        {"text": "Red floral packaging.", "value": "visual"},
        "Contains 2% hyaluronic acid",
        Fact(id=99, text="Alcohol-free formula", value="trivia"),
        "   ",
        {"id": 5, "text": "", "value": "core"},
    ]

    facts = normalize_facts(raw)
    assert len(facts) == 4
    assert facts[0] == Fact(id=10, text="Net weight is 40g.", value="core")
    assert facts[1] == Fact(id=2, text="Red floral packaging.", value="visual")
    assert facts[2] == Fact(id=3, text="Contains 2% hyaluronic acid", value="core")
    assert facts[3] == Fact(id=99, text="Alcohol-free formula", value="trivia")
    assert normalize_facts([]) == []
    assert normalize_facts(None) == []


def test_mock_verifier_supported_unsupported_and_contradicted_claims():
    facts = normalize_facts([
        {"id": 1, "text": "Net weight is 40 grams.", "value": "core"},
        {"id": 2, "text": "Contains 2% pure hyaluronic acid for 24-hour hydration.", "value": "core"},
        {"id": 3, "text": "Compressor comes with a 12-year guarantee.", "value": "core"},
    ])

    script = {
        "segment": "Skincare Shoppers",
        "lines": [
            {"id": 1, "kind": "hook", "text": "Feeling tired after a long commute?"},
            {"id": 2, "kind": "concept", "text": "This pack has 40 grams and contains 2% pure hyaluronic acid for 24-hour hydration."},
            {"id": 3, "kind": "concept", "text": "It is clinically proven by doctors with 50% off and free shipping today."},
            {"id": 4, "kind": "concept", "text": "The pack weighs 100 grams and includes a 2-year guarantee."},
            {"id": 5, "kind": "cta", "text": "Tap the link below to check it out!"},
        ],
    }

    result = verify_script_mock(script, facts)
    verdicts_by_line = {c.line_id: c for c in result.claims}

    # Hook (line 1) and generic CTA (line 5) carry no factual product claims
    assert 1 not in verdicts_by_line
    assert 5 not in verdicts_by_line

    # Line 2 matches facts 1 and 2
    assert verdicts_by_line[2].verdict == "supported"
    assert set(verdicts_by_line[2].matched_fact_ids) >= {1, 2}

    # Line 3 has ungrounded red-flag claims
    assert verdicts_by_line[3].verdict == "unsupported"
    assert verdicts_by_line[3].matched_fact_ids == []

    # Line 4 contradicts 40g (fact 1) and/or 12-year guarantee (fact 3)
    assert verdicts_by_line[4].verdict == "contradicted"
    assert len(verdicts_by_line[4].matched_fact_ids) >= 1


def test_mock_verifier_bengali_digits_and_missing_facts():
    bn_facts = normalize_facts([
        {"id": 1, "text": "The package net weight is 40 grams.", "value": "core"},
        {"id": 2, "text": "Contains cardamom and cinnamon.", "value": "core"},
    ])
    script = {
        "segment": "Home Cooks",
        "lines": [
            {"id": 1, "kind": "concept", "text": "এই ৪০ গ্রামের প্যাকেটে এলাচ ও দারুচিনি মেশানো আছে।"},
            {"id": 2, "kind": "concept", "text": "মাত্র ৩০ মিনিটে পুরো রান্না শেষ!"},
        ],
    }

    res = verify_script_mock(script, bn_facts)
    assert len(res.claims) == 2
    assert res.claims[0].verdict == "supported"
    assert 1 in res.claims[0].matched_fact_ids
    assert res.claims[1].verdict == "unsupported"

    # With empty facts, any extracted claim must be unsupported
    res_no_facts = verify_script_mock(script, [])
    assert len(res_no_facts.claims) == 2
    assert all(c.verdict == "unsupported" for c in res_no_facts.claims)


def test_edge_cases_empty_lines_and_missing_file(tmp_path: Path):
    assert extract_claims_mock([]) == []
    assert extract_claims_mock([{"id": 1, "kind": "hook", "text": "   "}]) == []

    empty_script_res = verify_script_mock({"segment": "Empty", "lines": []}, [])
    assert empty_script_res.claims == []

    with pytest.raises(FileNotFoundError):
        load_results_jsonl(tmp_path / "does_not_exist.jsonl")


@pytest.mark.asyncio
async def test_run_claim_check_mock_end_to_end(tmp_path: Path):
    jsonl_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "claim_check_report.md"
    json_out_path = tmp_path / "verdicts.jsonl"

    records = [
        {
            "product_id": "prod-dict-facts",
            "product_name": "Hydra Serum (30ml)",
            "category": "Skincare",
            "market": "Bangladesh",
            "language": "en",
            "facts": [
                {"id": 1, "text": "30ml dropper bottle with 2% hyaluronic acid.", "value": "core"},
            ],
            "scripts": [
                {
                    "segment": "Daily Commuters",
                    "lines": [
                        {"id": 1, "kind": "hook", "text": "Dry skin after office AC?"},
                        {"id": 2, "kind": "concept", "text": "This 30ml bottle contains 2% hyaluronic acid."},
                        {"id": 3, "kind": "cta", "text": "Grab yours from the store today."},
                    ],
                },
                {
                    "segment": "Students",
                    "lines": [
                        {"id": 1, "kind": "concept", "text": "Guaranteed 50% off with free shipping today!"},
                    ],
                },
            ],
        },
        {
            "product_id": "prod-str-facts",
            "product_name": "Plain String Product",
            "category": "General",
            "market": "Bangladesh",
            "language": "en",
            "facts": ["Made of 100% pure cotton."],
            "scripts": [
                {
                    "segment": "Empty Lines",
                    "lines": [],
                }
            ],
        },
    ]

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    summary, prod_results = await run_claim_check(
        input_path=jsonl_path,
        output_path=report_path,
        mock=True,
        json_out_path=json_out_path,
    )

    assert summary["products_evaluated"] == 2
    assert summary["total_scripts"] == 3
    assert summary["total_claims"] == 2
    assert summary["supported_claims"] == 1
    assert summary["unsupported_claims"] == 1
    assert summary["contradicted_claims"] == 0
    assert summary["unsupported_claim_rate_pct"] == 50.0
    assert summary["clean_scripts"] == 2
    assert len(prod_results) == 2

    report_text = report_path.read_text(encoding="utf-8")
    assert "# Claim Verification Evaluation Report" in report_text
    assert "Hydra Serum (30ml)" in report_text
    assert "[UNSUPPORTED]" in report_text
    assert json_out_path.exists()
    assert len(json_out_path.read_text(encoding="utf-8").strip().splitlines()) == 2


@pytest.mark.asyncio
async def test_run_claim_check_empty_jsonl(tmp_path: Path):
    empty_jsonl = tmp_path / "empty.jsonl"
    empty_jsonl.write_text("", encoding="utf-8")

    summary, prod_results = await run_claim_check(input_path=empty_jsonl, mock=True)
    assert summary["products_evaluated"] == 0
    assert summary["total_claims"] == 0
    assert summary["unsupported_claim_rate_pct"] == 0.0
    assert prod_results == []
    assert (tmp_path / "claim_check_report.md").exists()


@pytest.mark.asyncio
async def test_run_claim_check_baseline_smoke(tmp_path: Path):
    baseline_path = Path(__file__).resolve().parent.parent / "evals" / "results" / "baseline" / "results.jsonl"
    assert baseline_path.exists()

    summary, prod_results = await run_claim_check(
        input_path=baseline_path,
        output_path=tmp_path / "baseline_report.md",
        mock=True,
        limit=2,
    )
    assert summary["products_evaluated"] == 2
    assert summary["total_scripts"] == 6
    assert len(prod_results) == 2
    assert (tmp_path / "baseline_report.md").exists()


@pytest.mark.asyncio
async def test_run_claim_check_live_mode_with_mocked_genai(tmp_path: Path):
    jsonl_path = tmp_path / "live.jsonl"
    report_path = tmp_path / "live_report.md"
    record = {
        "product_id": "test-tea",
        "product_name": "Test Tea (200g)",
        "category": "Food & Beverage",
        "market": "Bangladesh",
        "language": "en",
        "facts": [{"id": 1, "text": "200g pack of hand-picked black tea.", "value": "core"}],
        "scripts": [
            {
                "segment": "Tea Lovers",
                "lines": [
                    {"id": 1, "kind": "concept", "text": "This 200g pack uses hand-picked black tea."},
                    {"id": 2, "kind": "concept", "text": "Winner of Best Tea 2026 award."},
                ],
            }
        ],
    }
    jsonl_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    mock_parsed = ScriptClaimCheckResult(
        claims=[
            ClaimVerdict(
                line_id=1,
                claim="200g pack uses hand-picked black tea",
                verdict="supported",
                matched_fact_ids=[1],
                rationale="Matches Fact #1.",
            ),
            ClaimVerdict(
                line_id=2,
                claim="Winner of Best Tea 2026 award",
                verdict="unsupported",
                matched_fact_ids=[],
                rationale="Award is not in facts.",
            ),
        ]
    )
    mock_response = SimpleNamespace(
        parsed=mock_parsed,
        text=mock_parsed.model_dump_json(),
        usage_metadata=SimpleNamespace(
            prompt_token_count=120,
            candidates_token_count=45,
            total_token_count=165,
        ),
    )

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    summary, _ = await run_claim_check(
        input_path=jsonl_path,
        output_path=report_path,
        mock=False,
        client=mock_client,
    )

    assert mock_client.aio.models.generate_content.await_count == 1
    assert summary["total_claims"] == 2
    assert summary["supported_claims"] == 1
    assert summary["unsupported_claims"] == 1
    assert summary["total_tokens"] == 165
    report_text = report_path.read_text(encoding="utf-8")
    assert "Winner of Best Tea 2026 award" in report_text


def test_get_vertex_client_requires_project(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setattr("evals.claim_check.load_dotenv", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="GOOGLE_CLOUD_PROJECT"):
        get_vertex_client()


def test_aggregate_claim_metrics_counts_errors():
    summary = aggregate_claim_metrics([
        {
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            "scripts": [{"segment": "S1", "claims": [], "error": "API timeout"}],
        }
    ])
    assert summary["errors"] == 1
    assert summary["clean_scripts"] == 0
