"""
Unit tests for Phase 4 (Format Setting & FORMAT_SPECS) and Phase 5 (Planning Fields & ScriptDraft).
"""

from unittest.mock import patch

from prompts import (
    FORMAT_SPECS,
    FormatSpec,
    build_language_block,
    build_script_prompt,
    SCRIPT_PROMPT,
    REWRITE_SCRIPT_PROMPT,
)
from schemas import (
    Line,
    Reason,
    Script,
    ScriptDraft,
    ScriptPlan,
    Segment,
    ScriptRewriteRequest,
)
from validation import validate_script, Issue


def test_format_specs_defined():
    """Verify UGC and Commercial 30s specifications are correctly configured."""
    assert "ugc" in FORMAT_SPECS
    assert "commercial_30s" in FORMAT_SPECS

    ugc = FORMAT_SPECS["ugc"]
    assert ugc.id == "ugc"
    assert ugc.word_range == (60, 90)
    assert ugc.hook_max_words == 10
    assert ugc.hook_hard_limit == 12
    assert ugc.use_speaker_visual is False
    assert len(ugc.hook_styles) >= 3

    comm = FORMAT_SPECS["commercial_30s"]
    assert comm.id == "commercial_30s"
    assert comm.word_range == (65, 80)
    assert comm.hook_max_words == 12
    assert comm.hook_hard_limit == 14
    assert comm.use_speaker_visual is True
    assert len(comm.hook_styles) >= 3


def test_script_draft_conversion():
    """Verify that ScriptDraft converts to a valid client-facing Script."""
    plan = ScriptPlan(
        core_promise="Instant 24h skin barrier hydration",
        lead_angle_ids=[1, 3],
        proof_moment="Dropper applying serum to dehydrated arm showing immediate absorption",
        objection="Is it sticky or greasy under makeup?",
        techniques=["Curiosity Hook", "Macro Texture Demo", "Confidence CTA"],
    )
    lines = [
        Line(id=1, kind="hook", text="Tired of your moisturizer vanishing before noon?", speaker="Voiceover (VO)", visual="Extreme close-up of dry skin"),
        Line(id=2, kind="concept", text="This serum seals in hydration with 2% pure hyaluronic acid.", speaker="On-camera host", visual="Product dropper demo on wrist"),
        Line(id=3, kind="cta", text="Grab yours today and feel the difference all day.", speaker="Voiceover (VO)", visual="Final product hero shot with bottle"),
    ]
    reasons = [
        Reason(title="Curiosity Hook", why="Addresses daytime dryness immediately", line_ids=[1]),
        Reason(title="Macro Texture Demo", why="Visual proof of non-sticky finish", line_ids=[2]),
        Reason(title="Confidence CTA", why="Clear action step", line_ids=[3]),
    ]
    draft = ScriptDraft(plan=plan, lines=lines, reasons=reasons)

    script = draft.to_script(segment_name="Desk Workers")
    assert isinstance(script, Script)
    assert script.segment == "Desk Workers"
    assert len(script.lines) == 3
    assert script.lines[0].speaker == "Voiceover (VO)"
    assert script.lines[0].visual == "Extreme close-up of dry skin"
    assert len(script.reasons) == 3


def test_validate_script_ugc_word_counts():
    """UGC scripts should enforce 60-90 words and <= 10 words hook."""
    lines = [
        Line(id=1, kind="hook", text="One two three four five six seven eight nine ten eleven twelve thirteen."),  # 13 words > 10
        Line(id=2, kind="concept", text="This is short."),
        Line(id=3, kind="cta", text="Buy now."),
    ]
    reasons = [
        Reason(title="T1", why="W1", line_ids=[1]),
        Reason(title="T2", why="W2", line_ids=[2]),
        Reason(title="T3", why="W3", line_ids=[3]),
    ]
    script = Script(segment="Test", lines=lines, reasons=reasons)

    issues = validate_script(script, language="en", format_spec="ugc")
    issue_codes = {i.code for i in issues}
    assert "hook_length_hard" in issue_codes
    assert "word_count_low" in issue_codes


def test_validate_script_commercial_checks():
    """Commercial 30s checks soft warnings when speaker tags are omitted."""
    lines = [
        Line(id=1, kind="hook", text="Start your day with pristine energy."),
        Line(id=2, kind="concept", text="Crafted with pure organic botanicals for enduring focus and vitality."),
        Line(id=3, kind="cta", text="Available now at all leading stores nationwide."),
    ]
    reasons = [
        Reason(title="T1", why="W1", line_ids=[1]),
        Reason(title="T2", why="W2", line_ids=[2]),
        Reason(title="T3", why="W3", line_ids=[3]),
    ]
    script_without_speakers = Script(segment="Test", lines=lines, reasons=reasons)

    issues = validate_script(script_without_speakers, language="en", format_spec="commercial_30s")
    assert any(i.code == "missing_speaker_tags" and i.severity == "soft" for i in issues)

    # Now add speaker tags
    lines_with_speakers = [
        Line(id=1, kind="hook", text="Start your day with pristine energy.", speaker="Voiceover"),
        Line(id=2, kind="concept", text="Crafted with pure organic botanicals for enduring focus and vitality.", speaker="Talent"),
        Line(id=3, kind="cta", text="Available now at all leading stores nationwide.", speaker="Voiceover"),
    ]
    script_with_speakers = Script(segment="Test", lines=lines_with_speakers, reasons=reasons)
    issues2 = validate_script(script_with_speakers, language="en", format_spec="commercial_30s")
    assert not any(i.code == "missing_speaker_tags" for i in issues2)


def test_build_language_block_bengali_transliteration():
    """Verify that build_language_block explicitly permits phonetic transliteration for Bengali loanwords."""
    ugc_bn = build_language_block("bn", "ugc")
    assert "বাংলা" in ugc_bn
    assert "phonetically in Bengali script" in ugc_bn
    assert "Customer segments" in ugc_bn

    comm_bn = build_language_block("bn", "commercial_30s")
    assert "broadcast and digital video commercials" in comm_bn
    assert "speaker tags, visual cues, and plan fields MUST ALWAYS remain in English" in comm_bn


def test_build_script_prompt():
    """Verify prompt formatting interpolates all spec variables cleanly without KeyErrors."""
    seg = Segment(name="Fitness Buffs", who="Gym goers 20-35", pain_point="Need fast post-workout protein", platforms=["Instagram"])
    prompt = build_script_prompt(
        prompt_template=SCRIPT_PROMPT,
        name="OptiWhey Protein",
        category="Fitness Nutrition",
        market="Bangladesh",
        language="en",
        segment=seg,
        facts_block="- [CORE] 25g pure whey protein per scoop",
        hook_style="Cold-Open Scene",
        script_format="commercial_30s",
    )
    assert "OptiWhey Protein" in prompt
    assert "Fitness Nutrition" in prompt
    assert "Fitness Buffs" in prompt
    assert "65-80 words spoken total" in prompt
    assert "speaker: For each line, specify the speaker role" in prompt
    assert "plan: First, commit to the strategic creative plan" in prompt
