"""
Tests for Sprint 4 Evaluation Harness and Deterministic Metrics.
"""

from pathlib import Path
import pytest
from schemas import Line, Reason, Script
from evals.metrics import (
    calculate_bengali_ratio,
    check_banned_phrases,
    check_repetition_loops,
    count_words,
    evaluate_script,
)
from evals.run import load_product_fixtures, run_harness


def test_count_words_and_bengali_ratio():
    en_text = "Stop scrolling if your skin feels dry by 2 PM!"
    bn_text = "প্রতিদিন অফিস শেষে শরীর ক্লান্ত লাগছে?"

    assert count_words(en_text) == 10
    assert count_words(bn_text) == 6
    assert calculate_bengali_ratio(bn_text) >= 0.95
    assert calculate_bengali_ratio(en_text) == 0.0


def test_banned_phrases_detection():
    dirty_en = "This revolutionary formula is a true game-changer!"
    clean_en = "This lightweight serum absorbs quickly without leaving sticky residue."

    assert "revolutionary" in check_banned_phrases(dirty_en, "en")
    assert "game-changer" in check_banned_phrases(dirty_en, "en")
    assert len(check_banned_phrases(clean_en, "en")) == 0


def test_repetition_loops_detection():
    degenerate_bn = "অওককক কককককককক ককককককককককক অকক কককক"
    clean_bn = "বন্ধুদের সাথে আড্ডা দিতে গিয়ে আইসক্রিম মুখে দিলেই দাঁত শিরশির করে ওঠে।"

    assert len(check_repetition_loops(degenerate_bn)) >= 1
    assert len(check_repetition_loops(clean_bn)) == 0


def test_evaluate_script_hard_rules():
    valid_script = Script(
        segment="Commuters",
        lines=[
            Line(id=1, kind="hook", text="If your energy crashes at 3 PM, listen to this."),
            Line(id=2, kind="concept", text="Humid weather completely drains your stamina during daily travel."),
            Line(id=3, kind="concept", text="This formula replenishes essential hydration with zero sticky feeling."),
            Line(id=4, kind="concept", text="Just two drops every morning keeps your focus clear all day."),
            Line(id=5, kind="concept", text="You will notice a genuine difference in daily vitality within two weeks."),
            Line(id=6, kind="cta", text="Tap the link below to get yours delivered to your doorstep today."),
        ],
        reasons=[
            Reason(title="Hook", why="Stops the scroll.", line_ids=[1]),
            Reason(title="Benefit", why="Highlights zero stickiness.", line_ids=[3, 4]),
            Reason(title="CTA", why="Direct action link.", line_ids=[6]),
        ],
    )

    ev = evaluate_script(valid_script, language="en", word_range=(40, 80))
    assert ev["first_line_is_hook"] is True
    assert ev["last_line_is_cta"] is True
    assert ev["reasons_valid"] is True
    assert ev["all_hard_rules_pass"] is True


@pytest.mark.asyncio
async def test_run_eval_harness_mock_smoke():
    summary, records = await run_harness(
        label="test_smoke_run",
        format_type="ugc",
        language_filter="all",
        limit=2,
        mock=True,
    )

    assert summary["products_evaluated"] == 2
    assert summary["total_scripts"] == 6
    assert len(records) == 2
    assert summary["structure_pass_rate"] == 100.0
