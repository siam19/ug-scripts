"""
Grounding and gating module for Sprint 4 Phase 2.

Enforces two-tier grounding:
1. sanitize_references: Drops non-existent fact IDs from angles; drops claim-bearing
   angles left with no valid grounding; drops invalid lead_angle_ids from segments.
2. gate_and_repair_segments: Ensures every customer segment has at least one claim-bearing
   lead angle (benefit, demo, objection). Assigns prioritized fallbacks if missing.
3. build_segment_script_context: Selects all core facts + any visual/trivia facts
   referenced by lead angles + the segment's lead angles.
4. format_grounding_prompt_block: Formats the selected facts and angles into prompt text.
"""

from typing import Sequence
from schemas import CLAIM_BEARING, Angle, Fact, Segment, Segments, coerce_facts_list


def sanitize_references(segments_data: Segments) -> Segments:
    """
    Sanitizes references across facts, angles, and customer segments:
    - Drops based_on fact IDs that do not exist in product_facts.
    - Drops claim-bearing angles (benefit, demo, objection) left with no valid fact grounding.
    - Drops lead_angle_ids that do not exist in the valid angles set.
    """
    valid_fact_ids = {f.id for f in segments_data.product_facts}

    sanitized_angles: list[Angle] = []
    for angle in segments_data.angles:
        sanitized_based_on = [fid for fid in angle.based_on if fid in valid_fact_ids]
        # Claim-bearing angles MUST cite at least one valid fact
        if angle.type in CLAIM_BEARING and not sanitized_based_on:
            continue
        sanitized_angles.append(
            angle.model_copy(update={"based_on": sanitized_based_on})
        )

    valid_angle_ids = {a.id for a in sanitized_angles}

    sanitized_segments: list[Segment] = []
    for seg in segments_data.segments:
        sanitized_lead = [aid for aid in seg.lead_angle_ids if aid in valid_angle_ids]
        sanitized_segments.append(
            seg.model_copy(update={"lead_angle_ids": sanitized_lead})
        )

    return segments_data.model_copy(
        update={
            "angles": sanitized_angles,
            "segments": sanitized_segments,
        }
    )


def gate_and_repair_segments(segments_data: Segments) -> Segments:
    """
    Gating check: verifies each segment has at least one claim-bearing lead angle.
    If a segment lacks a claim-bearing angle, assigns available claim-bearing angles
    with priority: benefit > demo > objection.
    If no claim-bearing angles exist in the product at all, synthesizes a benefit
    from the first available fact.
    """
    angles_list = list(segments_data.angles)
    angle_by_id = {a.id: a for a in angles_list}

    # Available claim-bearing angles in the product
    claim_bearing_angles = [a for a in angles_list if a.type in CLAIM_BEARING]
    claim_bearing_angles.sort(
        key=lambda a: 0 if a.type == "benefit" else (1 if a.type == "demo" else 2)
    )

    facts = segments_data.product_facts
    repaired_segments: list[Segment] = []

    for seg in segments_data.segments:
        has_claim_bearing = any(
            aid in angle_by_id and angle_by_id[aid].type in CLAIM_BEARING
            for aid in seg.lead_angle_ids
        )

        if has_claim_bearing:
            repaired_segments.append(seg)
            continue

        # Needs repair: assign up to 2 best claim-bearing angles
        new_lead = list(seg.lead_angle_ids)
        assigned = 0
        for cba in claim_bearing_angles:
            if cba.id not in new_lead:
                new_lead.append(cba.id)
                assigned += 1
                if assigned >= 2:
                    break

        # If still no claim-bearing angle exists in product, synthesize one from first fact
        if assigned == 0 and facts:
            first_fact = facts[0]
            synthetic_id = max((a.id for a in angles_list), default=0) + 1
            synthetic_angle = Angle(
                id=synthetic_id,
                type="benefit",
                text=f"Core benefit derived from {first_fact.text}",
                based_on=[first_fact.id],
                source="model",
            )
            angles_list.append(synthetic_angle)
            angle_by_id[synthetic_id] = synthetic_angle
            claim_bearing_angles.append(synthetic_angle)
            new_lead.append(synthetic_id)

        repaired_segments.append(seg.model_copy(update={"lead_angle_ids": new_lead}))

    return segments_data.model_copy(
        update={
            "angles": angles_list,
            "segments": repaired_segments,
        }
    )


def build_segment_script_context(
    segment: Segment,
    facts: Sequence[Fact | str],
    angles: Sequence[Angle] = (),
) -> tuple[list[Fact], list[Angle]]:
    """
    Builds the tailored facts and angles context for a specific segment's script generation:
    - All 'core' facts.
    - Any 'visual' or 'trivia' facts cited in based_on by the segment's lead angles.
    - The segment's lead angles.
    """
    # Normalize facts to Fact instances if string inputs were passed
    raw_facts = coerce_facts_list(list(facts))
    normalized_facts: list[Fact] = [
        f if isinstance(f, Fact) else Fact(**f) for f in raw_facts
    ]

    angle_by_id = {a.id: a for a in angles}
    lead_angles = [angle_by_id[aid] for aid in segment.lead_angle_ids if aid in angle_by_id]

    referenced_fact_ids = {fid for a in lead_angles for fid in a.based_on}

    selected_facts = [
        f for f in normalized_facts
        if f.value == "core" or f.id in referenced_fact_ids
    ]

    # Fallback to all facts if none were selected (e.g. no core facts and no references)
    if not selected_facts:
        selected_facts = normalized_facts

    return selected_facts, lead_angles


def format_grounding_prompt_block(
    facts: Sequence[Fact | str],
    angles: Sequence[Angle] = (),
) -> str:
    """
    Formats facts and angles into a clear two-tier grounding block for Gemini prompts.
    """
    raw_facts = coerce_facts_list(list(facts))
    normalized_facts: list[Fact] = [
        f if isinstance(f, Fact) else Fact(**f) for f in raw_facts
    ]

    lines: list[str] = [
        "VERIFIED PRODUCT FACTS (Grounding Truth - Every claim must trace to a fact):"
    ]
    for f in normalized_facts:
        lines.append(f"- [{f.value.upper()}] (Fact #{f.id}): {f.text}")

    if angles:
        lines.append("\nCREATIVE ANGLES (Inspiration for hooks, situations, feelings, and objections):")
        for a in angles:
            based_str = f" [Based on Fact #{', #'.join(str(i) for i in a.based_on)}]" if a.based_on else ""
            lines.append(f"- Angle #{a.id} [{a.type}]: {a.text}{based_str}")

    return "\n".join(lines)
