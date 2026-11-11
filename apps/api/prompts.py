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
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Pipeline and Prompt Versioning (Sprint 4: Format Setting & Planning)
# ---------------------------------------------------------------------------
PIPELINE_VERSION = "s4.0"
PROMPT_VERSIONS: dict[str, str] = {
    "segment": "v4.0",
    "script": "v4.0",
    "regenerate_segment": "v2.0",
    "rewrite_script": "v4.0",
    "rewrite_reason_lines": "v1.0",
    "rephrase_line": "v1.0",
    "regenerate_line": "v1.0",
}


@dataclass(frozen=True)
class FormatSpec:
    id: str
    label: str
    ad_context: str
    word_range: tuple[int, int]
    hook_max_words: int
    hook_hard_limit: int
    voice: str
    structure: str
    hook_styles: list[str]
    use_speaker_visual: bool


FORMAT_SPECS: dict[str, FormatSpec] = {
    "ugc": FormatSpec(
        id="ugc",
        label="UGC Video",
        ad_context="short-form UGC creator video ads (TikTok, Instagram Reels, YouTube Shorts)",
        word_range=(60, 90),
        hook_max_words=10,
        hook_hard_limit=12,
        voice="First-person creator on a smartphone camera. Relatable, casual, candid, authentic, conversational. Never corporate or announcer-stiff.",
        structure="Fast hook (0-3s, must stop the scroll), authentic body demonstrating the problem/benefit, direct natural CTA.",
        hook_styles=["Curiosity Question", "Problem Callout", "Demo / Before-After"],
        use_speaker_visual=True,
    ),
    "commercial_30s": FormatSpec(
        id="commercial_30s",
        label="30s Commercial",
        ad_context="high-impact 30-second digital video & TV commercial advertisements",
        word_range=(65, 80),
        hook_max_words=12,
        hook_hard_limit=14,
        voice="Polished brand voice, cinematic storytelling, voiceover (VO) or on-camera talent. High production value, confident, memorable.",
        structure="Cinematic cold-open / hook (0-3s), problem-solution narrative or product hero reveal, strong brand tagline & CTA.",
        hook_styles=["Cold-Open Scene", "Slice-of-Life Problem", "Product-as-Hero Reveal"],
        use_speaker_visual=True,
    ),
}

HOOKS = ["Curiosity Question", "Problem Callout", "Demo / Before-After"]
LANGUAGES: dict[str, str] = {"en": "English", "bn": "Bangla"}


# ---------------------------------------------------------------------------
# Shared language enforcement block injected into every prompt.
# Format variables: {language_name}, {language_code}
# ---------------------------------------------------------------------------

def build_language_block(language_code: str, script_format: str = "ugc") -> str:
    """
    Returns the language instruction block adapted for language and script format.
    Allows Bengali phonetic transliteration of technical/brand loanwords to prevent loop collapse.
    """
    lang_name = LANGUAGES.get(language_code, "English")
    if language_code == "bn":
        if script_format == "ugc":
            return (
                f"LANGUAGE INSTRUCTION:\n"
                f"- ONLY the spoken video script dialogue lines (hook, concept, cta) must be written in {lang_name} ({language_code}).\n"
                f"- Spoken dialogue must be in natural, conversational Bengali script (বাংলা) used by authentic UGC creators in Bangladesh.\n"
                f"- You MAY write English technical, brand, and ingredient loanwords phonetically in Bengali script "
                f"(e.g., 'হাইড্রোক্সিপ্যাটাইট', 'এনামেল', 'ব্রাশ', 'অর্গানিক', 'ক্রিম'). This prevents awkward translations.\n"
                f"- DO NOT output Latin-script English sentences for dialogue.\n"
                f"- Customer segments, marketing reasons (title, why), and plan fields MUST ALWAYS remain strictly in English."
            )
        else:  # commercial_30s
            return (
                f"LANGUAGE INSTRUCTION:\n"
                f"- ONLY the spoken video script dialogue lines (hook, concept, cta) must be written in {lang_name} ({language_code}).\n"
                f"- Use polished, high-standard contemporary Bengali script (বাংলা) suitable for broadcast and digital video commercials.\n"
                f"- English brand and technical loanwords are permitted in Bengali script where standard in commercial advertising.\n"
                f"- Customer segments, marketing reasons, speaker tags, visual cues, and plan fields MUST ALWAYS remain in English."
            )
    else:  # English
        if script_format == "ugc":
            return (
                "LANGUAGE INSTRUCTION:\n"
                "- Write dialogue in crisp, conversational, authentic spoken English for creator video.\n"
                "- Customer segments, reasons, and plan fields must be in English."
            )
        else:
            return (
                "LANGUAGE INSTRUCTION:\n"
                "- Write dialogue in polished, persuasive, high-impact commercial English suitable for TV/digital advertising.\n"
                "- Customer segments, reasons, and plan fields must be in English."
            )


LANGUAGE_BLOCK = build_language_block("en", "ugc")


# ---------------------------------------------------------------------------
# Stage 1: Multi-modal extraction (Sprint 4: Two-Tier Grounding)
# Format variables: {name}, {category}, {description}, {market}, {ad_context}
# ---------------------------------------------------------------------------

SEGMENT_PROMPT = """You are a performance-marketing strategist for {ad_context} in {market}.

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
# Stage 2: Full script generation (Sprint 4: Planning & Format Specs)
# Format variables: {name}, {category}, {facts}, {segment_name}, {who},
#                   {pain_point}, {hook}, {market}, {language}, {ad_context},
#                   {voice}, {min_words}, {max_words}, {hook_max_words},
#                   {speaker_visual_instructions}, {language_block}
# ---------------------------------------------------------------------------

SCRIPT_PROMPT = """You write scripts for {ad_context} in {market}.
Write spoken dialogue in {language}.
Voice & tone: {voice}

{language_block}

PRODUCT: {name} ({category})

GROUNDING FACTS & CREATIVE ANGLES:
{facts}

TARGET AUDIENCE:
Segment: {segment_name}
Who: {who}
Pain point: {pain_point}
Hook style: {hook}

TASK
1. plan: First, commit to the strategic creative plan for this script before writing dialogue:
   - core_promise: The single primary outcome promised to this audience segment.
   - lead_angle_ids: Which creative angle IDs are actively executed in this script.
   - proof_moment: The specific visible demonstration or evidence beat shown on camera to prove the claim.
   - objection: The main customer friction addressed.
   - techniques: Exactly 3 performance marketing techniques used (in English).

2. lines: Write the ready-to-film spoken dialogue lines conforming strictly to your committed plan:
   - Length: {min_words}-{max_words} words spoken total.
   - Structure: hook (first line, 0-3s, must stop the scroll), concept (body lines), cta (last line).
   - Hook length: <= {hook_max_words} words.
   - Line numbering: strictly sequential from 1.
   {speaker_visual_instructions}

3. reasons: Exactly 3 performance marketing rationales in English explaining why the chosen techniques work for this segment and list the contiguous line_ids that demonstrate each technique.

RULES:
- TWO-TIER GROUNDING: Every claim about the product must trace to a listed fact. Situations, feelings, objections and demonstrations come from the listed angles and your creativity.
- Do not state an angle as an unverified product guarantee. Trivia facts may appear only as passing visual detail.
- No medical claims, no '#1', no made-up numbers or testimonials.
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

REWRITE_SCRIPT_PROMPT = """You write scripts for {ad_context} in {market}.
Write spoken dialogue in {language}.
Voice & tone: {voice}

{language_block}

PRODUCT: {name} ({category})
GROUNDING FACTS & CREATIVE ANGLES:
{facts}
TARGET: {segment_name}: {who}. Pain point: {pain_point}
HOOK STYLE: {hook}

TASK
1. plan: First, commit to the strategic creative plan for this script before writing dialogue:
   - core_promise: The single primary outcome promised to this audience segment.
   - lead_angle_ids: Which creative angle IDs are actively executed in this script.
   - proof_moment: The specific visible demonstration or evidence beat shown on camera to prove the claim.
   - objection: The main customer friction addressed.
   - techniques: Exactly 3 performance marketing techniques used (in English).

2. lines: Write a FRESH, complete ready-to-film script conforming strictly to your committed plan:
   - Length: {min_words}-{max_words} words spoken total.
   - Structure: hook (first line, 0-3s, must stop the scroll), concept (body lines), cta (last line).
   - Hook length: <= {hook_max_words} words.
   - Line numbering: strictly sequential from 1.
   {speaker_visual_instructions}

3. reasons: Exactly 3 performance marketing rationales in English explaining why the chosen techniques work for this segment and list the contiguous line_ids that demonstrate each technique.

RULES:
- TWO-TIER GROUNDING: Every claim about the product must trace to a listed fact. Situations, feelings, objections and demonstrations come from the listed angles and your creativity.
- Do not state an angle as an unverified product guarantee. Trivia facts may appear only as passing visual detail.
- No medical claims, no '#1', no made-up numbers or testimonials.
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


def build_script_prompt(
    prompt_template: str,
    name: str,
    category: str,
    market: str,
    language: str,
    segment: Any,
    facts_block: str,
    hook_style: str,
    script_format: str = "ugc",
) -> str:
    """Builds the fully interpolated prompt for ScriptDraft generation based on FormatSpec."""
    spec = FORMAT_SPECS.get(script_format, FORMAT_SPECS["ugc"])
    lang_name = LANGUAGES.get(language, language)
    lang_block = build_language_block(language, script_format)

    if spec.use_speaker_visual:
        if spec.id == "commercial_30s":
            speaker_visual_instructions = (
                "- speaker: For each line, specify the speaker role (e.g. 'Voiceover (VO)', 'On-camera talent', 'Customer').\n"
                "- visual: For each line, provide a concise visual direction cue (<= 12 words, in English) describing what is shown on screen."
            )
        else:
            speaker_visual_instructions = (
                "- visual: For each line, provide a concise visual direction cue (<= 12 words, in English) describing what the creator shows or does on camera (e.g. holding product, reacting to camera, demoing texture)."
            )
    else:
        speaker_visual_instructions = (
            "- speaker and visual: Leave null / omit for UGC scripts."
        )

    segment_name = getattr(segment, "name", "") if hasattr(segment, "name") else segment.get("name", "")
    who = getattr(segment, "who", "") if hasattr(segment, "who") else segment.get("who", "")
    pain_point = getattr(segment, "pain_point", "") if hasattr(segment, "pain_point") else segment.get("pain_point", "")

    return prompt_template.format(
        name=name,
        category=category,
        market=market,
        language=lang_name,
        facts=facts_block,
        segment_name=segment_name,
        who=who,
        pain_point=pain_point,
        hook=hook_style,
        ad_context=spec.ad_context,
        voice=spec.voice,
        min_words=spec.word_range[0],
        max_words=spec.word_range[1],
        hook_max_words=spec.hook_max_words,
        speaker_visual_instructions=speaker_visual_instructions,
        language_block=lang_block,
    )



