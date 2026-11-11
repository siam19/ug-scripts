"""
Tests for apps/api/validation.py: in-code deterministic validation and single retry.
"""

from unittest.mock import AsyncMock
import pytest
from schemas import Line, Reason, ReasonLinesRewriteResponse, RewrittenLine, Script
from validation import (
    Issue,
    ask_validated,
    build_correction_prompt,
    validate_reason_lines_rewrite,
    validate_script,
)


def create_valid_script(language: str = "en") -> Script:
    """Helper creating a fully conforming Script fixture."""
    if language == "bn":
        lines = [
            Line(id=1, kind="hook", text="প্রতিদিন অফিস শেষে শরীর ক্লান্ত লাগছে?"),
            Line(id=2, kind="concept", text="ঢাকার এই অসহ্য গরম আর জ্যামে সারাদিন কাজ করার পর এমন ক্লান্তি খুব স্বাভাবিক।"),
            Line(id=3, kind="concept", text="এই বিশেষ প্রাকৃতিক ফর্মুলা ক্লান্তি দূর করে ত্বকের ন্যাচারাল ব্যালান্স ফিরিয়ে আনে খুব দ্রুত।"),
            Line(id=4, kind="concept", text="কোন রকম ক্ষতিকর কেমিক্যাল বা চিটচিটে ভাব ছাড়া এটা দিনে দুইবার ব্যবহার করলেই পার্থক্য বুঝতে পারবেন।"),
            Line(id=5, kind="concept", text="মাত্র তিন সপ্তাহের নিয়মিত ব্যবহারে নিজের এনার্জি আর রিফ্রেশিং অনুভূতি চোখে পড়ার মতো বদলে যাবে।"),
            Line(id=6, kind="cta", text="দেরি ছাড়া নিজের বোতলটি পেতে এখনই নিচের লিংকে ট্যাপ করুন।"),
        ]
    else:
        lines = [
            Line(id=1, kind="hook", text="If your energy crashes every single afternoon, listen up."),
            Line(id=2, kind="concept", text="Running from meetings to errands in humid weather completely drains your daily focus."),
            Line(id=3, kind="concept", text="This lightweight formula was specifically engineered to restore sustained vitality without jitters."),
            Line(id=4, kind="concept", text="It absorbs cleanly within thirty seconds, leaving zero sticky residue behind on your skin."),
            Line(id=5, kind="concept", text="In just three weeks of daily morning use, you notice consistent stamina all afternoon."),
            Line(id=6, kind="cta", text="Tap the link below right now to get yours delivered to your doorstep."),
        ]

    reasons = [
        Reason(title="Hook", why="Stops scroll immediately.", line_ids=[1]),
        Reason(title="Mechanism", why="Explains quick absorption.", line_ids=[3, 4]),
        Reason(title="CTA", why="Direct action link.", line_ids=[6]),
    ]
    return Script(segment="Urban Professionals", lines=lines, reasons=reasons)


def test_valid_script_passes_with_no_hard_issues():
    script_en = create_valid_script("en")
    issues_en = validate_script(script_en, language="en")
    assert not any(i.severity == "hard" for i in issues_en)

    script_bn = create_valid_script("bn")
    issues_bn = validate_script(script_bn, language="bn")
    assert not any(i.severity == "hard" for i in issues_bn)


def test_validate_script_detects_long_hook():
    script = create_valid_script("en")
    # Hook with 16 words (> 12 hard limit)
    script.lines[0].text = "Stop what you are doing right now if you feel completely exhausted every single busy working day"
    issues = validate_script(script, language="en")
    codes = [i.code for i in issues]
    assert "hook_length_hard" in codes


def test_validate_script_detects_banned_phrases():
    script = create_valid_script("en")
    script.lines[1].text = "This revolutionary formula is a complete game-changer for your skin."
    issues = validate_script(script, language="en")
    codes = [i.code for i in issues]
    assert "banned_phrases" in codes


def test_validate_script_detects_repetition_loops():
    script = create_valid_script("bn")
    # Repetition mode collapse
    script.lines[2].text = "অকক অকককক ককককককককককক কককককককক অকক"
    issues = validate_script(script, language="bn")
    codes = [i.code for i in issues]
    assert "repetition_loop" in codes


def test_validate_script_detects_line_kind_boundaries():
    script = create_valid_script("en")
    script.lines[0].kind = "concept"  # First line not hook
    script.lines[2].kind = "hook"     # Intermediate hook
    script.lines[-1].kind = "concept" # Last line not cta

    issues = validate_script(script, language="en")
    codes = [i.code for i in issues]
    assert "first_line_not_hook" in codes
    assert "intermediate_hook" in codes
    assert "last_line_not_cta" in codes


def test_validate_script_detects_invalid_and_non_contiguous_reasons():
    script = create_valid_script("en")
    # Non-existent line ID 99
    script.reasons[0].line_ids = [99]
    # Non-contiguous line IDs [2, 5]
    script.reasons[1].line_ids = [2, 5]

    issues = validate_script(script, language="en")
    codes = [i.code for i in issues]
    assert "reason_invalid_line_id" in codes
    assert "reason_citations_non_contiguous" in codes


def test_validate_script_word_count_limits():
    script = create_valid_script("en")
    # Too short: only 10 words
    script.lines = [
        Line(id=1, kind="hook", text="Tired today?"),
        Line(id=2, kind="cta", text="Buy now."),
    ]
    issues = validate_script(script, language="en")
    codes = [i.code for i in issues]
    assert "word_count_low" in codes


def test_validate_reason_lines_rewrite_boundary_preservation():
    resp = ReasonLinesRewriteResponse(
        lines=[
            RewrittenLine(kind="concept", text="Rewritten line 1 text."),
            RewrittenLine(kind="concept", text="Rewritten line 2 text."),
        ]
    )
    # Line 1 was targeted, but returned as 'concept' instead of 'hook'
    issues = validate_reason_lines_rewrite(
        resp,
        target_line_ids=[1, 2],
        total_script_lines=6,
        language="en",
    )
    codes = [i.code for i in issues]
    assert "hook_boundary_violation" in codes


@pytest.mark.asyncio
async def test_ask_validated_succeeds_on_retry():
    bad_script = create_valid_script("en")
    bad_script.lines[0].text = "Stop scrolling right now if you are looking for the absolute greatest product in the world today"

    good_script = create_valid_script("en")

    mock_ask = AsyncMock()
    mock_ask.side_effect = [bad_script, good_script]

    result, issues = await ask_validated(
        mock_ask,
        prompt="Original prompt",
        schema=Script,
        stage="script",
        validate=lambda s: validate_script(s, language="en"),
    )

    assert mock_ask.call_count == 2
    assert not any(i.severity == "hard" for i in issues)
    assert result == good_script


@pytest.mark.asyncio
async def test_ask_validated_returns_best_attempt_when_retry_fails():
    attempt1 = create_valid_script("en")
    attempt1.lines[0].text = "Stop scrolling right now if you are looking for the absolute greatest product in the world today" # 1 hard issue

    attempt2 = create_valid_script("en")
    attempt2.lines[0].text = "Stop scrolling right now if you are looking for the absolute greatest product in the world today"
    attempt2.lines[1].text = "This game-changer is a true miracle." # 2 hard issues

    mock_ask = AsyncMock()
    mock_ask.side_effect = [attempt1, attempt2]

    result, issues = await ask_validated(
        mock_ask,
        prompt="Original prompt",
        schema=Script,
        stage="script",
        validate=lambda s: validate_script(s, language="en"),
    )

    assert mock_ask.call_count == 2
    # Returns attempt 1 because it has fewer hard issues
    assert result == attempt1
    assert any(i.severity == "hard" for i in issues)


@pytest.mark.asyncio
async def test_ask_validated_lowers_temperature_on_repetition_loop():
    degenerate_script = create_valid_script("bn")
    degenerate_script.lines[1].text = "অকক অকককক ককককককককককক কককককককক"

    recovered_script = create_valid_script("bn")

    mock_ask = AsyncMock()
    mock_ask.side_effect = [degenerate_script, recovered_script]

    await ask_validated(
        mock_ask,
        prompt="Original prompt",
        schema=Script,
        stage="script",
        temperature=0.7,
        validate=lambda s: validate_script(s, language="bn"),
    )

    # Second call should have temperature=0.2
    retry_call_kwargs = mock_ask.call_args_list[1].kwargs
    assert retry_call_kwargs["temperature"] == 0.2
