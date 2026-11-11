"""
Deterministic Metric Evaluator for Generated Scripts (Sprint 4 Eval Harness).

Evaluates structural constraints, word counts, hook brevity, banned cliché detection,
Bengali script ratio, and reason citation integrity without any external LLM dependencies.
"""

import re
import string
from typing import Any
from schemas import Script

# Initial banned cliches (infomercial phrases forbidden in authentic creator UGC)
BANNED_PHRASES = {
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

# Regex to strip standard punctuation (preserving whitespace)
PUNCT_TABLE = str.maketrans("", "", string.punctuation + "।‘’“”")


def count_words(text: str) -> int:
    """Counts words by stripping punctuation and splitting on whitespace."""
    cleaned = text.translate(PUNCT_TABLE).strip()
    if not cleaned:
        return 0
    return len(cleaned.split())


def calculate_bengali_ratio(text: str) -> float:
    """
    Calculates the ratio of Bengali script characters (Unicode U+0980 to U+09FF)
    over all non-whitespace, non-digit, non-punctuation alphabetic characters.
    Returns 1.0 if empty or entirely Bengali.
    """
    total_letters = 0
    bengali_letters = 0
    for char in text:
        if char.isspace() or char.isdigit() or char in string.punctuation or char in "।‘ ’“”":
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
    
    # Check language-specific list
    phrases = BANNED_PHRASES.get(language, [])
    for phrase in phrases:
        if phrase in text_lower:
            hits.append(phrase)
            
    # Also check English cliches across all languages as safety
    if language != "en":
        for phrase in BANNED_PHRASES["en"]:
            if phrase in text_lower:
                hits.append(phrase)
                
    return hits


def check_repetition_loops(text: str) -> list[str]:
    """
    Detects degenerative character or word repetition loops (e.g. 'কককক', 'অকক অকক').
    Returns a list of detected repetition patterns.
    """
    hits: list[str] = []
    # 4 or more identical consecutive characters (e.g. 'কককক', 'aaaa')
    char_match = re.search(r'(.)\1{3,}', text)
    if char_match:
        hits.append(f"repeated_char: '{char_match.group(0)[:8]}'")
        
    # Check lexical diversity (unique words / total words)
    words = text.translate(PUNCT_TABLE).split()
    if len(words) >= 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.45:
            hits.append(f"low_lexical_diversity: {round(unique_ratio, 2)}")
            
    return hits


def evaluate_script(
    script: Script,
    language: str = "en",
    format_type: str = "ugc",
    word_range: tuple[int, int] = (60, 90),
    hook_max_words: int = 10,
) -> dict[str, Any]:
    """
    Calculates deterministic metrics for a single Script object.
    """
    lines = script.lines or []
    reasons = script.reasons or []
    
    dialogue_texts = [l.text for l in lines]
    combined_dialogue = " ".join(dialogue_texts)
    
    total_words = count_words(combined_dialogue)
    hook_words = count_words(lines[0].text) if lines else 0
    
    first_line_is_hook = (lines[0].kind == "hook") if lines else False
    last_line_is_cta = (lines[-1].kind == "cta") if lines else False
    
    # Check no intermediate hooks
    intermediate_hooks = [l.id for l in lines[1:] if l.kind == "hook"]
    no_intermediate_hooks = (len(intermediate_hooks) == 0)
    
    # Reason checks
    reasons_count_ok = (len(reasons) == 3)
    
    all_line_ids = {l.id for l in lines}
    cited_ids_valid = True
    cites_contiguous = True
    
    for r in reasons:
        cites = r.line_ids or []
        if not cites or not all(cid in all_line_ids for cid in cites):
            cited_ids_valid = False
        else:
            # Check contiguous
            if len(cites) > 1 and cites != list(range(cites[0], cites[0] + len(cites))):
                cites_contiguous = False
                
    # Banned phrase check
    banned_hits = check_banned_phrases(combined_dialogue, language)
    
    # Repetition loop check
    repetition_hits = check_repetition_loops(combined_dialogue)
    
    # Bengali ratio (for Bangla scripts)
    bengali_ratio = calculate_bengali_ratio(combined_dialogue) if language == "bn" else 1.0
    
    # Hard rule checks
    hard_passes = (
        first_line_is_hook
        and last_line_is_cta
        and no_intermediate_hooks
        and reasons_count_ok
        and cited_ids_valid
        and (len(banned_hits) == 0)
        and (len(repetition_hits) == 0)
        and (bengali_ratio >= 0.65 if language == "bn" else True)
    )
    
    word_range_pass = (word_range[0] * 0.9 <= total_words <= word_range[1] * 1.1)
    hook_length_pass = (hook_words <= hook_max_words * 1.2)
    
    return {
        "segment": script.segment,
        "line_count": len(lines),
        "total_words": total_words,
        "word_range_pass": word_range_pass,
        "hook_words": hook_words,
        "hook_length_pass": hook_length_pass,
        "first_line_is_hook": first_line_is_hook,
        "last_line_is_cta": last_line_is_cta,
        "no_intermediate_hooks": no_intermediate_hooks,
        "reasons_count": len(reasons),
        "reasons_count_ok": reasons_count_ok,
        "reasons_valid": cited_ids_valid and cites_contiguous,
        "banned_hits": banned_hits,
        "repetition_hits": repetition_hits,
        "bengali_ratio": bengali_ratio,
        "all_hard_rules_pass": hard_passes and word_range_pass,
    }


def aggregate_run_metrics(eval_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregates metric stats across an entire evaluation run.
    """
    total_scripts = 0
    total_hard_pass = 0
    total_words_sum = 0
    hook_words_sum = 0
    total_banned_hits = 0
    total_repetition_hits = 0
    word_range_passes = 0
    hook_length_passes = 0
    structure_passes = 0
    bengali_ratios: list[float] = []
    
    ttfc_times: list[float] = []
    total_times: list[float] = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0

    for item in eval_records:
        timing = item.get("timing", {})
        if "ttfc_sec" in timing:
            ttfc_times.append(timing["ttfc_sec"])
        if "total_sec" in timing:
            total_times.append(timing["total_sec"])
            
        usage = item.get("usage", {})
        total_input_tokens += usage.get("input_tokens", 0)
        total_output_tokens += usage.get("output_tokens", 0)
        total_tokens += usage.get("total_tokens", 0)

        for s_eval in item.get("script_evals", []):
            total_scripts += 1
            words = s_eval["total_words"]
            total_words_sum += words
            hook_words_sum += s_eval["hook_words"]
            
            if s_eval["all_hard_rules_pass"]:
                total_hard_pass += 1
            if s_eval["word_range_pass"]:
                word_range_passes += 1
            if s_eval["hook_length_pass"]:
                hook_length_passes += 1
            if (
                s_eval["first_line_is_hook"]
                and s_eval["last_line_is_cta"]
                and s_eval["no_intermediate_hooks"]
                and s_eval["reasons_valid"]
            ):
                structure_passes += 1
                
            if s_eval["banned_hits"]:
                total_banned_hits += len(s_eval["banned_hits"])
            if s_eval.get("repetition_hits"):
                total_repetition_hits += len(s_eval["repetition_hits"])
                
            if item.get("language") == "bn":
                bengali_ratios.append(s_eval["bengali_ratio"])

    n_scripts = max(1, total_scripts)
    n_products = max(1, len(eval_records))

    return {
        "products_evaluated": len(eval_records),
        "total_scripts": total_scripts,
        "overall_hard_pass_rate": round((total_hard_pass / n_scripts) * 100, 1),
        "structure_pass_rate": round((structure_passes / n_scripts) * 100, 1),
        "word_range_pass_rate": round((word_range_passes / n_scripts) * 100, 1),
        "hook_length_pass_rate": round((hook_length_passes / n_scripts) * 100, 1),
        "avg_words_per_script": round(total_words_sum / n_scripts, 1),
        "avg_hook_words": round(hook_words_sum / n_scripts, 1),
        "total_banned_phrase_hits": total_banned_hits,
        "banned_hit_rate_pct": round((total_banned_hits / n_scripts) * 100, 1),
        "total_repetition_hits": total_repetition_hits,
        "repetition_hit_rate_pct": round((total_repetition_hits / n_scripts) * 100, 1),
        "avg_bengali_script_ratio": round(sum(bengali_ratios) / max(1, len(bengali_ratios)), 3) if bengali_ratios else 1.0,
        "avg_ttfc_sec": round(sum(ttfc_times) / max(1, len(ttfc_times)), 2) if ttfc_times else 0.0,
        "avg_total_latency_sec": round(sum(total_times) / max(1, len(total_times)), 2) if total_times else 0.0,
        "avg_tokens_per_product": round(total_tokens / n_products, 0),
        "total_tokens_consumed": total_tokens,
    }
