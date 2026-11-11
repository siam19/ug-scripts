"""
Prompt templates for the Script Assistant pipeline.

These prompts power the two-stage generation process and Sprint 2 granular regeneration actions:
1. SEGMENT_PROMPT: Stage 1 multi-modal extraction of verifiable facts and 3 differentiated segments.
2. SCRIPT_PROMPT: Stage 2 parallel script generation for each segment, adhering to allocated hook styles.
3. REGENERATE_SEGMENT_PROMPT: Replace a single customer segment with a fresh, unique persona.
4. REWRITE_SCRIPT_PROMPT: Rewrite an entire script for a (possibly edited) segment against updated facts.
5. REWRITE_REASON_LINES_PROMPT: Rewrite the contiguous line group cited by a specific marketing technique.
6. REPHRASE_LINE_PROMPT: Rephrase a single line into an alternative tone while preserving meaning.
7. REGENERATE_LINE_PROMPT: Replace a single line with a completely new angle fitting the same position.

Every regeneration prompt embeds a LANGUAGE INSTRUCTION block to enforce strict
adherence to the user's selected language (English or Bangla).
"""
from typing import Any

# ---------------------------------------------------------------------------
# Pipeline and Prompt Versioning (Sprint 4)
# ---------------------------------------------------------------------------
PIPELINE_VERSION = "s4.0"
PROMPT_VERSIONS: dict[str, str] = {
    "segment": "v2.0",
    "script": "v2.0",
    "regenerate_segment": "v2.0",
    "rewrite_script": "v2.0",
    "rewrite_reason_lines": "v1.0",
    "rephrase_line": "v1.0",
    "regenerate_line": "v1.0",
}

# ---------------------------------------------------------------------------
# Shared language enforcement block injected into every regeneration prompt.
# Format variables: {language_name}, {language_code}
# ---------------------------------------------------------------------------

LANGUAGE_BLOCK = """LANGUAGE INSTRUCTION:
- ONLY the spoken video script dialogue lines (hook, concept, cta) must be written in {language_name} ({language_code}).
- Customer segments (name, who, pain_point, platforms), product facts, and marketing rationale (reasons: title, why) MUST ALWAYS be written in English.
- If language is 'Bangla' (bn):
  * Spoken video script dialogue lines (hook, concept, cta) must be written in proper, natural Bengali script (বাংলা).
  * Write dialogue in conversational, authentic spoken Bangla used by UGC creators in Bangladesh.
  * DO NOT transliterate English into Bengali script (no "Banglish").
  * DO NOT output English sentences for spoken dialogue lines.
  * Customer segments, marketing reasons, and platform names MUST remain strictly in English.
- If language is 'English' (en):
  * Use crisp, natural, conversational spoken English for script dialogue lines.
"""

# ---------------------------------------------------------------------------
# Stage 1: Multi-modal extraction (Sprint 4: Two-Tier Grounding)
# Format variables: {name}, {category}, {description}, {market}
# ---------------------------------------------------------------------------

SEGMENT_PROMPT = """You are a performance-marketing strategist for short-form UGC video ads
(TikTok, Reels, Shorts) in {market}.

PRODUCT
Name: {name}
Category: {category}
Description: {description}
The attached image is the product photo. Read it closely: packaging
text, ingredients/specs, colors, size cues, shape, anything a viewer notices.

LANGUAGE REQUIREMENT:
- All product facts, product appearance, creative angles, and customer segments MUST ALWAYS be written in English.

TASK
1. product_facts: 5-8 concrete, verifiable facts drawn ONLY from the description and image in English.
   Seller-provided description claims outrank photo-derived ones. No invented claims.
   For each fact:
   - id: sequential 1-based integer (1, 2, 3...)
   - text: concise factual statement
   - value:
     * "core": what the product is or does, key specifications, seller guarantees, materials, capacity
     * "visual": visible product attribute (color, pattern, shape, packaging look)
     * "trivia": minor detail that rarely persuades on its own (small labels, fittings, minor design details)

2. product_appearance: 2-3 sentences describing what the product looks like (shape, colors, materials, packaging) from the photo.

3. angles: 8-12 creative angles spanning a healthy mix of claim-bearing and framing types.
   Claim-bearing types assert something about the product and MUST cite at least one fact id in based_on:
   - "benefit": an outcome the buyer gets, inferred from a fact (based_on: [fact_id, ...])
   - "demo": something that can be shown on camera to visually prove a fact (based_on: [fact_id, ...])
   - "objection": a hesitation or friction the buyer has + fact-backed answer (based_on: [fact_id, ...])
   Framing types set up situation or feeling and MUST NOT assert product capabilities (based_on is optional/empty):
   - "use_moment": a specific situation in which the product is used
   - "identity": how the buyer wants to feel or be seen
   - "contrast": the buyer's current frustrating alternative / status quo without naming competitors
   - "audience_context": cultural or market reality shaping the buyer's routine
   For each angle: id (1..N), type, text, based_on (list of fact ids).

4. segments: exactly 3 customer segments most likely to buy in English.
   They must differ in motivation and lifestyle, not just age.
   For each:
   - name: clear, descriptive persona title
   - who: demographics, life situation, daily context
   - pain_point: core frustration or desire in their own words
   - platforms: 1-3 short-form platforms
   - lead_angle_ids: list of 2-3 angle IDs from above that this segment's ad should lead with (must include at least one claim-bearing angle).
"""

# ---------------------------------------------------------------------------
# Stage 2: Full script generation (Sprint 4: Two-Tier Grounding)
# Format variables: {name}, {category}, {facts}, {segment_name}, {who},
#                   {pain_point}, {hook}, {market}, {language}
# ---------------------------------------------------------------------------

SCRIPT_PROMPT = """You write scripts that a creator films on a phone for a short-form ad in
{market}. Write in {language}, spoken and natural, never ad-copy stiff.

PRODUCT: {name} ({category})

GROUNDING FACTS & CREATIVE ANGLES:
{facts}

TARGET: {segment_name}: {who}. Pain point: {pain_point}
HOOK STYLE: {hook}

RULES
- 20-35 seconds spoken (about 60-90 words).
- Structure: hook (first 3 seconds, must stop the scroll), concept, cta.
  Tag each line with its kind and number lines from 1.
- TWO-TIER GROUNDING RULE:
  * Every claim about the product must trace to a listed fact.
  * Situations, scenes, feelings, objections and demonstrations come from the listed angles and your own creativity.
  * Do not state an angle as an unverified product guarantee.
  * Trivia facts may appear only as passing visual detail, never as the central claim of a line.
  * No medical claims, no '#1', no made-up numbers or testimonials.
- Speak to this segment's pain point, not to everyone.
- reasons: exactly 3. Each names a specific technique in English (pattern
  interrupt, specificity, objection handling, demo/proof, etc.),
  explains in English why it works for THIS segment, and lists the line_ids that
  use it. The title and why fields of each reason MUST ALWAYS be in English. Never cite a line that does not do what you claim.
"""

# ---------------------------------------------------------------------------
# Sprint 2: Regenerate a single customer segment
# Format variables: {name}, {category}, {market}, {language_name},
#                   {language_code}, {facts}, {current_segment_name},
#                   {current_segment_who}, {current_segment_pain_point},
#                   {other_segment_names}
# ---------------------------------------------------------------------------

REGENERATE_SEGMENT_PROMPT = """You are a performance-marketing strategist for short-form UGC video ads
(TikTok, Reels, Shorts) in {market}.

PRODUCT: {name} ({category})

PRODUCT FACTS:
{facts}

LANGUAGE REQUIREMENT:
- All customer segment details (name, who, pain_point, platforms) MUST ALWAYS be written in English.
- Even if the target market is Bangladesh or the chosen script language is Bangla, the customer segment personas MUST REMAIN IN ENGLISH. Only the spoken video script itself will be in Bengali.
- Do NOT output Bengali script (বাংলা) anywhere in this response.

TASK
Generate ONE new customer segment that would be a strong buyer of this
product. This segment must be COMPLETELY DIFFERENT from all of the
following existing segments:
- Current segment being replaced: "{current_segment_name}" — {current_segment_who}
{other_segment_names}

REQUIREMENTS
- The new segment must differ in motivation, lifestyle, and daily
  context — not just demographics or age.
- All fields must be strictly in English.
- name: A vivid, specific persona title in English (not generic like "young adults").
- who: Age range, life situation, daily context, and buying motivation in English.
- pain_point: The core frustration or desire expressed in this persona's
  own natural words in English — first person, emotionally specific.
- platforms: 1-3 short-form video platforms where this persona is most
  active.
- Be creative and specific. The new segment must NOT overlap with any of
  the existing segments listed above.
"""

# ---------------------------------------------------------------------------
# Sprint 2: Rewrite an entire script for a (possibly edited) segment
# Format variables: {name}, {category}, {market}, {language_name},
#                   {language_code}, {facts}, {segment_name}, {who},
#                   {pain_point}, {hook}, {language_block}
# ---------------------------------------------------------------------------

REWRITE_SCRIPT_PROMPT = """You write scripts that a creator films on a phone for a short-form ad
in {market}.

{language_block}

PRODUCT: {name} ({category})
GROUNDING FACTS & CREATIVE ANGLES:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}
HOOK STYLE: {hook}

TASK
Write a complete, ready-to-film UGC script for this target segment.
This is a FRESH rewrite — do not copy or paraphrase any previous version.

RULES
- 20-35 seconds spoken (about 60-90 words).
- Structure: hook (first 3 seconds, must stop the scroll), concept, cta.
  Tag each line with its kind and number lines from 1.
- TWO-TIER GROUNDING RULE:
  * Every claim about the product must trace to a listed fact.
  * Situations, scenes, feelings, objections and demonstrations come from the listed angles and your own creativity.
  * Do not state an angle as an unverified product guarantee.
  * Trivia facts may appear only as passing visual detail, never as the central claim of a line.
  * No medical claims, no '#1', no made-up numbers or testimonials.
- Speak directly to this segment's pain point, not to a generic audience.
- reasons: exactly 3. Each names a specific technique in English (pattern
  interrupt, specificity, objection handling, demo/proof, etc.),
  explains in English why it works for THIS segment, and lists the line_ids that
  use it. Cited line_ids must be contiguous. The title and why fields of each reason MUST ALWAYS be in English. Never cite a line that
  does not demonstrate the claimed technique.
"""

# ---------------------------------------------------------------------------
# Sprint 2: Rewrite the contiguous line group cited by a marketing technique
# Format variables: {name}, {market}, {language_name}, {language_code},
#                   {facts}, {segment_name}, {who}, {pain_point},
#                   {full_script}, {target_positions}, {reason_title},
#                   {reason_why}, {language_block}
# ---------------------------------------------------------------------------

REWRITE_REASON_LINES_PROMPT = """You are rewriting part of a short-form UGC video script for a creator
filming on their phone in {market}.

{language_block}

PRODUCT: {name}
FACTS YOU MAY USE:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}

THE FULL CURRENT SCRIPT (for context and flow):
{full_script}

TECHNIQUE TO STRENGTHEN
Title: {reason_title}
Why it works for this segment: {reason_why}

LINES TO REPLACE (positions {target_positions}):
{target_lines}

TASK
Write replacement lines for positions {target_positions} that STRENGTHEN
the "{reason_title}" technique while fitting seamlessly into the
surrounding script. The replacement lines must:

RULES
- Match the tone, vocabulary, and pacing of the surrounding lines.
- Maintain narrative coherence: the lines before and after the replaced
  block must still flow naturally.
- If the target includes line 1, the first replacement MUST be kind "hook"
  (opening 3-second scroll-stopper).
- If the target includes the last line of the script, the final
  replacement MUST be kind "cta" (call to action).
- Middle lines should be kind "concept" unless the technique demands
  otherwise.
- Use ONLY the product facts listed above. No invented claims.
- The count of replacement lines may differ slightly from the original
  if necessary to fulfill the technique, but keep the total script
  between 20-35 seconds spoken.
- Return ONLY the replacement lines as a list, each with kind and text.
  Do NOT return the full script.
"""

# ---------------------------------------------------------------------------
# Sprint 2: Rephrase a single line in an alternative tone
# Format variables: {name}, {market}, {language_name}, {language_code},
#                   {facts}, {segment_name}, {who}, {pain_point},
#                   {script_context}, {line_id}, {current_text}, {kind},
#                   {avoid_tones}, {language_block}
# ---------------------------------------------------------------------------

REPHRASE_LINE_PROMPT = """You are rewriting a single line from a short-form UGC video script.
The creator films on their phone in {market}.

{language_block}

PRODUCT: {name}
FACTS YOU MAY USE:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}

SURROUNDING SCRIPT (for context):
{script_context}

LINE TO REPHRASE (line {line_id}, kind: {kind}):
"{current_text}"

TASK
Rephrase this line using a DIFFERENT TONE while keeping the exact same
core meaning — same subject, same object, same core claim. The sentence
structure and wording must clearly change; do not just swap one word.

AVAILABLE TONES (pick one):
- punchy: Ultra-concise, fast tempo, high impact. Short sentences.
- casual: Friendly, relatable, everyday friend giving advice.
- authentic: Honest, no-hype, genuine user experience. Understated.
- direct: Clear instruction, focused benefit, no fluff.

{avoid_tones}

RULES
- Output exactly ONE rephrased line.
- The rephrased text must be in {language_name}.
- The kind stays "{kind}" — do not change the line's structural role.
- Use only the product facts listed above.
- Return the rephrased text and the tone tag you chose.
"""

# ---------------------------------------------------------------------------
# Sprint 2: Regenerate a single line with a completely new angle
# Format variables: {name}, {market}, {language_name}, {language_code},
#                   {facts}, {segment_name}, {who}, {pain_point},
#                   {script_context}, {line_id}, {current_text}, {kind},
#                   {language_block}
# ---------------------------------------------------------------------------

REGENERATE_LINE_PROMPT = """You are writing a replacement line for a short-form UGC video script.
The creator films on their phone in {market}.

{language_block}

PRODUCT: {name}
FACTS YOU MAY USE:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}

SURROUNDING SCRIPT (for context):
{script_context}

LINE TO REPLACE (line {line_id}, kind: {kind}):
"{current_text}"

TASK
Write a COMPLETELY NEW line for position {line_id} that takes a
different angle or idea than the current text. Do NOT rephrase or
echo the old wording — come up with a fresh approach.

RULES
- The new line's kind MUST be "{kind}".
- If kind is "hook": it must stop the scroll within 3 seconds.
- If kind is "cta": it must drive a clear, immediate action.
- If kind is "concept": it must convey a compelling product truth.
- The new line must fit naturally between the lines before and after it
  in the script.
- Use only the product facts listed above. No invented claims.
- Output exactly ONE line with its text and kind.
- The text must be in {language_name}.
"""

# ---------------------------------------------------------------------------
# Prompt Formatting Helpers
# ---------------------------------------------------------------------------

LANGUAGES: dict[str, str] = {"en": "English", "bn": "Bangla"}


def get_language_block(language_code: str) -> str:
    """Returns the formatted LANGUAGE_BLOCK for 'en' or 'bn'."""
    lang_name = LANGUAGES.get(language_code, "English")
    return LANGUAGE_BLOCK.format(language_name=lang_name, language_code=language_code)


def format_facts_text(facts: Any) -> str:
    """Formats a list of Fact objects, dicts, or strings as bulleted lines."""
    lines = []
    for idx, f in enumerate(facts):
        if hasattr(f, "text"):
            val = getattr(f, "value", "core")
            fid = getattr(f, "id", idx + 1)
            lines.append(f"- [{val.upper()}] (Fact #{fid}): {f.text.strip()}")
        elif isinstance(f, dict):
            val = f.get("value", "core")
            fid = f.get("id", idx + 1)
            lines.append(f"- [{val.upper()}] (Fact #{fid}): {f.get('text', '').strip()}")
        else:
            lines.append(f"- {str(f).strip()}")
    return "\n".join(lines)


def format_script_context(lines: list[Any]) -> str:
    """Formats a sequence of script lines for prompt context."""
    return "\n".join(
        f"{getattr(l, 'id', idx + 1)}. [{getattr(l, 'kind', 'concept')}] {getattr(l, 'text', '')}"
        for idx, l in enumerate(lines)
    )


def format_avoid_tones(avoid_tones: list[str]) -> str:
    """Formats the avoid-tones constraint if any tones have already been attempted."""
    if not avoid_tones:
        return ""
    tones_str = ", ".join(avoid_tones)
    return f"DO NOT use any of these tones (already tried): {tones_str}. Select a DIFFERENT tone from the available options."


