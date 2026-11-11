"""
Deterministic In-Code Validation and Single-Retry Engine (Sprint 4).

Pure functions and validated execution wrapper to enforce prompt-level rules:
1. Hook brevity (<= 10 words soft, > 12 words hard)
2. Line kind boundaries (line 1 is hook, line N is cta, no intermediate hooks)
3. Reason citations (exactly 3 reasons, citing existing, contiguous line IDs)
4. Word count limits (within format range +- 10% tolerance)
5. Banned cliché detection (English and Bangla lists)
6. Repetition/degeneration loop detection (e.g. 'কককক' character loops, low lexical diversity)
7. Bengali script character ratio (>= 0.65 for Bangla dialogue)
"""

import re
import string
from dataclasses import dataclass
from typing import Any, Callable, Literal, Sequence
from google.genai import types

from schemas import Line, Reason, ReasonLinesRewriteResponse, Script
from prompts import FORMAT_SPECS, FormatSpec

# Default specification for UGC video scripts
UGC_DEFAULTS: dict[str, Any] = {
    "word_range": (60, 90),
    "hook_max_words": 10,
    "hook_hard_limit": 12,
    "use_speaker_visual": False,
}

# Punctuation stripping table (preserves whitespace)
PUNCT_TABLE = str.maketrans("", "", string.punctuation + "।‘’“”")

# Banned cliches (infomercial phrases forbidden in authentic UGC)
BANNED_PHRASES: dict[str, list[str]] = {
    "en": [
        "are you tired of",
        "say goodbye to",
        "look no further",
        "game-changer",
        "game changer",
        "revolutionary",
        "miracle",
        "100% guaranteed",
        "secret to",
        "don't walk, run",
        "stop what you're doing",
        "hurry up and",
        "you won't believe",
    ],
    "bn": [
        "আর চিন্তা নেই",
        "আজই অর্ডার করুন",
        "১০০% গ্যারান্টি",
        "চমৎকার সমাধান",
        "সেরা অফার",
        "দেরি না করে",
        "যাদুকরী",
        "অবিশ্বাস্য ফলাফল",
    ],
}


@dataclass
class Issue:
    """Represents a rule violation detected in a generated Script."""
    code: str
    severity: Literal["hard", "soft"]
    message: str


def count_words(text: str) -> int:
    """Counts words by stripping punctuation and splitting on whitespace."""
    cleaned = text.translate(PUNCT_TABLE).strip()
    if not cleaned:
        return 0
    return len(cleaned.split())


def calculate_bengali_ratio(text: str) -> float:
    """
    Calculates the ratio of Bengali script characters (Unicode U+0980 to U+09FF)
    over all alphabetic characters in dialogue.
    """
    total_letters = 0
    bengali_letters = 0
    for char in text:
        if char.isspace() or char.isdigit() or char in string.punctuation or char in "।‘’“”":
            continue
        total_letters += 1
        if "\u0980" <= char <= "\u09ff":
            bengali_letters += 1

    if total_letters == 0:
        return 1.0
    return round(bengali_letters / total_letters, 3)


def check_banned_phrases(text: str, language: str) -> list[str]:
    """Finds any banned phrase hits in text (case-insensitive)."""
    hits: list[str] = []
    text_lower = text.lower()
    
    phrases = BANNED_PHRASES.get(language, [])
    for phrase in phrases:
        if phrase in text_lower:
            hits.append(phrase)
            
    if language != "en":
        for phrase in BANNED_PHRASES["en"]:
            if phrase in text_lower:
                hits.append(phrase)
                
    return hits


def check_repetition_loops(text: str) -> list[str]:
    """
    Detects degenerative character or word repetition loops (e.g. 'কককক', 'অকক অকক').
    """
    hits: list[str] = []
    # 4 or more identical consecutive characters
    char_match = re.search(r'(.)\1{3,}', text)
    if char_match:
        hits.append(f"repeated character pattern: '{char_match.group(0)[:8]}'")
        
    # Check lexical diversity (unique words / total words)
    words = text.translate(PUNCT_TABLE).split()
    if len(words) >= 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.45:
            hits.append(f"low lexical diversity (repetitive vocabulary): {round(unique_ratio, 2)}")
            
    return hits


def validate_script(
    script: Any,
    language: str = "en",
    format_spec: dict[str, Any] | FormatSpec | str | None = None,
) -> list[Issue]:
    """
    Validates a generated Script or ScriptDraft against deterministic quality and structural constraints.
    Returns a list of structured Issues.
    """
    issues: list[Issue] = []

    if isinstance(format_spec, str):
        spec = FORMAT_SPECS.get(format_spec, FORMAT_SPECS["ugc"])
        word_range = spec.word_range
        hook_max_words = spec.hook_max_words
        hook_hard_limit = spec.hook_hard_limit
        use_speaker_visual = spec.use_speaker_visual
    elif isinstance(format_spec, FormatSpec):
        word_range = format_spec.word_range
        hook_max_words = format_spec.hook_max_words
        hook_hard_limit = format_spec.hook_hard_limit
        use_speaker_visual = format_spec.use_speaker_visual
    elif isinstance(format_spec, dict):
        word_range = format_spec.get("word_range", (60, 90))
        hook_max_words = format_spec.get("hook_max_words", 10)
        hook_hard_limit = format_spec.get("hook_hard_limit", 12)
        use_speaker_visual = format_spec.get("use_speaker_visual", False)
    else:
        word_range = UGC_DEFAULTS["word_range"]
        hook_max_words = UGC_DEFAULTS["hook_max_words"]
        hook_hard_limit = UGC_DEFAULTS["hook_hard_limit"]
        use_speaker_visual = UGC_DEFAULTS["use_speaker_visual"]

    lines = getattr(script, "lines", []) or []
    reasons = getattr(script, "reasons", []) or []

    # 1. Line count and sequential check
    if not lines:
        issues.append(Issue(
            code="missing_lines",
            severity="hard",
            message="Script contains no dialogue lines.",
        ))
        return issues

    expected_ids = list(range(1, len(lines) + 1))
    actual_ids = [l.id for l in lines]
    if actual_ids != expected_ids:
        issues.append(Issue(
            code="line_ids_non_sequential",
            severity="hard",
            message=f"Line IDs must be strictly sequential 1..N. Found: {actual_ids}",
        ))

    # 2. First line hook & last line cta check
    if lines[0].kind != "hook":
        issues.append(Issue(
            code="first_line_not_hook",
            severity="hard",
            message=f"Line 1 kind must be 'hook', but got '{lines[0].kind}'.",
        ))

    if lines[-1].kind != "cta":
        issues.append(Issue(
            code="last_line_not_cta",
            severity="hard",
            message=f"Last line (line {lines[-1].id}) kind must be 'cta', but got '{lines[-1].kind}'.",
        ))

    intermediate_hooks = [l.id for l in lines[1:] if l.kind == "hook"]
    if intermediate_hooks:
        issues.append(Issue(
            code="intermediate_hook",
            severity="hard",
            message=f"Only line 1 can be a 'hook'. Found additional hooks at lines: {intermediate_hooks}.",
        ))

    # 3. Hook brevity check
    hook_words = count_words(lines[0].text)
    if hook_words > hook_hard_limit:
        issues.append(Issue(
            code="hook_length_hard",
            severity="hard",
            message=f"Line 1 hook has {hook_words} words (maximum allowed is {hook_max_words}). Make it punchy and under {hook_max_words} words.",
        ))
    elif hook_words > hook_max_words:
        issues.append(Issue(
            code="hook_length_soft",
            severity="soft",
            message=f"Line 1 hook has {hook_words} words. Aim for <= {hook_max_words} words for maximum thumb-stopping power.",
        ))

    # 4. Total word count check
    dialogue_texts = [l.text for l in lines]
    combined_dialogue = " ".join(dialogue_texts)
    total_words = count_words(combined_dialogue)
    min_words, max_words = word_range

    hard_min = int(min_words * 0.9)
    hard_max = int(max_words * 1.1)

    if total_words < hard_min:
        issues.append(Issue(
            code="word_count_low",
            severity="hard",
            message=f"Total spoken script has {total_words} words, which is too short (target range: {min_words}-{max_words} words).",
        ))
    elif total_words > hard_max:
        issues.append(Issue(
            code="word_count_high",
            severity="hard",
            message=f"Total spoken script has {total_words} words, which is too long (target range: {min_words}-{max_words} words).",
        ))
    elif total_words < min_words or total_words > max_words:
        issues.append(Issue(
            code="word_count_edge",
            severity="soft",
            message=f"Total spoken script has {total_words} words (target range: {min_words}-{max_words} words).",
        ))

    # 5. Reason count and citation validity
    if len(reasons) != 3:
        issues.append(Issue(
            code="reasons_count_invalid",
            severity="hard",
            message=f"Script must contain exactly 3 technique reasons, but got {len(reasons)}.",
        ))

    all_line_ids = set(actual_ids)
    for i, reason in enumerate(reasons, 1):
        cites = reason.line_ids or []
        if not cites:
            issues.append(Issue(
                code="reason_missing_citations",
                severity="hard",
                message=f"Reason {i} ('{reason.title}') does not cite any line_ids.",
            ))
        elif not all(cid in all_line_ids for cid in cites):
            invalid_ids = [cid for cid in cites if cid not in all_line_ids]
            issues.append(Issue(
                code="reason_invalid_line_id",
                severity="hard",
                message=f"Reason {i} cites non-existent line_ids: {invalid_ids}.",
            ))
        else:
            # Check contiguity
            if len(cites) > 1 and cites != list(range(cites[0], cites[0] + len(cites))):
                issues.append(Issue(
                    code="reason_citations_non_contiguous",
                    severity="hard",
                    message=f"Reason {i} cites non-contiguous line_ids: {cites}. Cited lines must be contiguous.",
                ))

    # 6. Banned cliché detection
    banned_hits = check_banned_phrases(combined_dialogue, language)
    if banned_hits:
        issues.append(Issue(
            code="banned_phrases",
            severity="hard",
            message=f"Found forbidden marketing clichés in dialogue: {banned_hits}. Replace them with authentic creator language.",
        ))

    # 7. Repetition/degeneration loop detection
    repetition_hits = check_repetition_loops(combined_dialogue)
    if repetition_hits:
        issues.append(Issue(
            code="repetition_loop",
            severity="hard",
            message=f"Dialogue contains degenerative repetition loops: {repetition_hits}. Rewrite with natural, varied vocabulary and no repeated characters.",
        ))

    # 8. Bengali script ratio (for Bangla)
    if language == "bn":
        bengali_ratio = calculate_bengali_ratio(combined_dialogue)
        if bengali_ratio < 0.65:
            issues.append(Issue(
                code="bengali_ratio_low",
                severity="hard",
                message=f"Bengali dialogue has a script ratio of {bengali_ratio} (minimum 0.65 required). Ensure spoken lines are written in Bengali script.",
            ))

    # 9. Commercial 30s speaker tag check (soft)
    if use_speaker_visual:
        missing_speaker = [l.id for l in lines if not getattr(l, "speaker", None)]
        if len(missing_speaker) == len(lines):
            issues.append(Issue(
                code="missing_speaker_tags",
                severity="soft",
                message="Commercial 30s scripts should specify 'speaker' roles (e.g. 'Voiceover', 'On-camera talent').",
            ))

    return issues


def build_correction_prompt(
    original_prompt: str,
    previous_script: Script,
    hard_issues: list[Issue],
) -> str:
    """
    Builds a targeted correction prompt instructing Gemini to fix numbered violations.
    """
    issue_lines = [f"{i}. {issue.message}" for i, issue in enumerate(hard_issues, 1)]
    issues_text = "\n".join(issue_lines)

    lines_preview = "\n".join(f"[{l.id} - {l.kind}] {l.text}" for l in (previous_script.lines or []))

    return f"""{original_prompt}

IMPORTANT CORRECTION REQUIRED:
Your previous output violated strict quality and structure constraints:
{issues_text}

Previous dialogue output:
{lines_preview}

Please rewrite the script to resolve ALL of the violations above while preserving product facts and audience context.
"""


def validate_reason_lines_rewrite(
    response: ReasonLinesRewriteResponse,
    target_line_ids: list[int],
    total_script_lines: int,
    language: str = "en",
) -> list[Issue]:
    """
    Validates rewritten contiguous reason lines, preserving kind boundaries.
    """
    issues: list[Issue] = []
    lines = response.lines or []
    target_sorted = sorted(target_line_ids)

    if not lines:
        issues.append(Issue(
            code="missing_rewritten_lines",
            severity="hard",
            message="Rewritten lines response was empty.",
        ))
        return issues

    if 1 in target_sorted and lines[0].kind != "hook":
        issues.append(Issue(
            code="hook_boundary_violation",
            severity="hard",
            message="Line 1 was rewritten but its kind was not preserved as 'hook'.",
        ))

    if total_script_lines in target_sorted and lines[-1].kind != "cta":
        issues.append(Issue(
            code="cta_boundary_violation",
            severity="hard",
            message=f"Last line ({total_script_lines}) was rewritten but its kind was not preserved as 'cta'.",
        ))

    combined = " ".join(l.text for l in lines)
    banned = check_banned_phrases(combined, language)
    if banned:
        issues.append(Issue(
            code="banned_phrases",
            severity="hard",
            message=f"Rewritten lines contained banned clichés: {banned}",
        ))

    rep_hits = check_repetition_loops(combined)
    if rep_hits:
        issues.append(Issue(
            code="repetition_loop",
            severity="hard",
            message=f"Rewritten lines contained repetition loops: {rep_hits}",
        ))

    return issues


def build_reason_lines_correction_prompt(
    original_prompt: str,
    previous_response: ReasonLinesRewriteResponse,
    hard_issues: list[Issue],
) -> str:
    issue_lines = [f"{i}. {issue.message}" for i, issue in enumerate(hard_issues, 1)]
    issues_text = "\n".join(issue_lines)
    lines_preview = "\n".join(f"[{l.kind}] {l.text}" for l in (previous_response.lines or []))
    return f"""{original_prompt}

IMPORTANT CORRECTION REQUIRED:
Your rewritten lines violated the following constraints:
{issues_text}

Previous lines:
{lines_preview}

Please rewrite the lines resolving all violations.
"""


async def ask_validated(
    ask_fn: Callable[..., Any],
    *,
    prompt: str,
    schema: type[Any],
    parts: Sequence[Any] = (),
    stage: str = "script",
    temperature: float | None = None,
    system_instruction: str | None = None,
    validate: Callable[[Any], list[Issue]],
    build_correction: Callable[[str, Any, list[Issue]], str] = build_correction_prompt,
    max_validation_retries: int = 1,
) -> tuple[Any, list[Issue]]:
    """
    Executes a structured model generation with in-code validation and single targeted retry.
    Returns (best_attempt, remaining_issues). Never raises on validation failure.
    """
    # 1. First attempt
    first_attempt = await ask_fn(
        prompt=prompt,
        schema=schema,
        parts=parts,
        stage=stage,
        temperature=temperature,
        system_instruction=system_instruction,
    )

    first_issues = validate(first_attempt)
    first_hard = [i for i in first_issues if i.severity == "hard"]

    # If no hard issues, return immediately
    if not first_hard or max_validation_retries <= 0:
        return first_attempt, first_issues

    # 2. Build targeted correction prompt
    correction_prompt = build_correction(prompt, first_attempt, first_hard)

    # If repetition loop was detected, lower temperature to escape sampling trap
    retry_temperature = temperature
    if any(i.code == "repetition_loop" for i in first_hard):
        retry_temperature = 0.2

    try:
        second_attempt = await ask_fn(
            prompt=correction_prompt,
            schema=schema,
            parts=parts,
            stage=stage,
            temperature=retry_temperature,
            system_instruction=system_instruction,
        )
        second_issues = validate(second_attempt)
        second_hard = [i for i in second_issues if i.severity == "hard"]

        # Keep attempt with fewer hard issues
        if len(second_hard) <= len(first_hard):
            return second_attempt, second_issues
        return first_attempt, first_issues

    except Exception as e:
        # If retry call fails at network/model level, gracefully fall back to first attempt
        first_issues.append(Issue(
            code="validation_retry_failed",
            severity="soft",
            message=f"Validation retry attempt failed: {str(e)}",
        ))
        return first_attempt, first_issues

