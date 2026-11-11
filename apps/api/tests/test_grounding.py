"""
Unit tests for Sprint 4 Phase 2 grounding, reference sanitization, segment gating,
and context building.
"""

from schemas import Angle, Fact, Segment, Segments
from grounding import (
    build_segment_script_context,
    format_grounding_prompt_block,
    gate_and_repair_segments,
    sanitize_references,
)


def test_sanitize_references_drops_invalid_facts_and_ungrounded_claims():
    facts = [
        Fact(id=1, text="Made with 100% Arabica beans", value="core"),
        Fact(id=2, text="Packaged in dark amber glass jar", value="visual"),
    ]
    angles = [
        # Valid claim-bearing citing fact 1
        Angle(id=10, type="benefit", text="Rich crema without bitterness", based_on=[1]),
        # Invalid claim-bearing citing non-existent fact 99 -> should be dropped
        Angle(id=11, type="benefit", text="Invented miracle energy", based_on=[99]),
        # Partially valid claim-bearing citing 1 and 99 -> 99 stripped, kept with [1]
        Angle(id=12, type="demo", text="Watch the crema form", based_on=[1, 99]),
        # Framing angle citing non-existent 99 -> 99 stripped, framing angle KEPT
        Angle(id=13, type="use_moment", text="The 7am morning calm", based_on=[99]),
    ]
    segments = [
        Segment(
            name="Early Birds",
            who="Morning workers",
            pain_point="Need quick quality coffee",
            platforms=["TikTok"],
            lead_angle_ids=[10, 11, 13, 999],  # 11 and 999 are invalid
        )
    ]
    segs = Segments(
        product_facts=facts,
        product_appearance="Amber jar with gold lid.",
        angles=angles,
        segments=segments,
    )

    sanitized = sanitize_references(segs)

    # Angle 11 dropped because it's claim-bearing with no valid fact
    angle_ids = [a.id for a in sanitized.angles]
    assert 11 not in angle_ids
    assert 10 in angle_ids
    assert 12 in angle_ids
    assert 13 in angle_ids

    # Angle 12 based_on cleaned to [1]
    a12 = next(a for a in sanitized.angles if a.id == 12)
    assert a12.based_on == [1]

    # Angle 13 based_on cleaned to []
    a13 = next(a for a in sanitized.angles if a.id == 13)
    assert a13.based_on == []

    # Segment lead_angle_ids cleaned to [10, 13]
    assert sanitized.segments[0].lead_angle_ids == [10, 13]


def test_gate_and_repair_segments_assigns_claim_bearing_fallback():
    facts = [
        Fact(id=1, text="Lightweight aluminium body", value="core"),
    ]
    angles = [
        Angle(id=1, type="use_moment", text="On a rainy evening", based_on=[]),
        Angle(id=2, type="benefit", text="Easy to carry all day without fatigue", based_on=[1]),
    ]
    # Segment leads ONLY with framing angle 1
    segments = [
        Segment(
            name="Commuters",
            who="Daily subway riders",
            pain_point="Heavy bags hurt shoulders",
            platforms=["Reels"],
            lead_angle_ids=[1],
        )
    ]
    segs = Segments(product_facts=facts, angles=angles, segments=segments)

    repaired = gate_and_repair_segments(segs)

    # Commuters should now include claim-bearing angle 2
    assert 2 in repaired.segments[0].lead_angle_ids


def test_gate_and_repair_synthesizes_angle_if_none_exist():
    facts = [
        Fact(id=1, text="Contains SPF 50+ mineral filter", value="core"),
    ]
    # No angles exist
    segments = [
        Segment(
            name="Beachgoers",
            who="Outdoor enthusiasts",
            pain_point="Sunburn risk",
            platforms=["TikTok"],
            lead_angle_ids=[],
        )
    ]
    segs = Segments(product_facts=facts, angles=[], segments=segments)

    repaired = gate_and_repair_segments(segs)

    assert len(repaired.angles) >= 1
    synthetic = repaired.angles[0]
    assert synthetic.type == "benefit"
    assert synthetic.based_on == [1]
    assert synthetic.id in repaired.segments[0].lead_angle_ids


def test_build_segment_script_context_filters_trivia_unless_referenced():
    facts = [
        Fact(id=1, text="24-hour battery life", value="core"),
        Fact(id=2, text="Matte black finish", value="visual"),
        Fact(id=3, text="CE regulatory stamp on bottom", value="trivia"),
        Fact(id=4, text="Includes 15cm USB-C cable in box", value="trivia"),
    ]
    angles = [
        # Cites trivia fact 4
        Angle(id=10, type="demo", text="Unbox the compact charging cable", based_on=[4]),
    ]
    segment = Segment(
        name="Tech Reviewers",
        who="Gadget lovers",
        pain_point="Tired of carrying multiple cables",
        platforms=["YouTube Shorts"],
        lead_angle_ids=[10],
    )

    selected_facts, lead_angles = build_segment_script_context(segment, facts, angles)

    selected_fact_ids = [f.id for f in selected_facts]
    # Fact 1 is core -> included
    assert 1 in selected_fact_ids
    # Fact 4 is trivia but referenced by lead angle 10 -> included
    assert 4 in selected_fact_ids
    # Fact 2 (visual) and 3 (trivia) not referenced -> excluded
    assert 2 not in selected_fact_ids
    assert 3 not in selected_fact_ids

    assert len(lead_angles) == 1
    assert lead_angles[0].id == 10


def test_format_grounding_prompt_block_formats_tiers():
    facts = [
        Fact(id=1, text="Noise cancellation up to 35dB", value="core"),
    ]
    angles = [
        Angle(id=5, type="demo", text="Snap fingers near ear to show silence", based_on=[1]),
    ]

    block = format_grounding_prompt_block(facts, angles)

    assert "VERIFIED PRODUCT FACTS" in block
    assert "[CORE] (Fact #1): Noise cancellation up to 35dB" in block
    assert "CREATIVE ANGLES" in block
    assert "Angle #5 [demo]: Snap fingers near ear to show silence [Based on Fact #1]" in block


def test_backward_compatibility_fact_coercion():
    raw_facts = [
        "First legacy fact as string",
        "Second legacy fact as string",
    ]
    segs = Segments(
        product_facts=raw_facts,
        segments=[
            Segment(name="Audience", who="Anyone", pain_point="None", platforms=["TikTok"])
        ],
    )

    assert len(segs.product_facts) == 2
    assert isinstance(segs.product_facts[0], Fact)
    assert segs.product_facts[0].id == 1
    assert segs.product_facts[0].text == "First legacy fact as string"
    assert segs.product_facts[0].value == "core"
    assert segs.product_facts[1].id == 2
