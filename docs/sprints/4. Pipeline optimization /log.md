# Sprint 4 Changelog: Pipeline Optimization & Quality

## Log Entry: Phase 0 Baseline, Evaluation Harness, & Plumbing

**Date**: 2026-11-11  
**Status**: Phase 0 Complete & Baseline Benchmark Established  
**Baseline Evaluation Report**: [`apps/api/evals/results/baseline/report.md`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/results/baseline/report.md)

---

### 1. Architectural & Backend Plumbing

* **`ask_gemini` Extended Signature ([`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py)):**
  - Updated `ask_gemini` to accept `stage: str = "unspecified"`, `temperature: float | None = None`, and `system_instruction: str | None = None`.
  - Configures `types.GenerateContentConfig` dynamically with temperature and system instructions when specified.
  - Tagged all API endpoints with explicit stage identifiers (`extract`, `script`, `regenerate_segment`, `rewrite_script`, `rewrite_reason_lines`, `rephrase_line`, `regenerate_line`).

* **Token Accounting by Pipeline Stage ([`apps/api/usage.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/usage.py), [`apps/api/schemas.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/schemas.py)):**
  - Added `StageTokens` schema model and added `by_stage: dict[str, StageTokens] = Field(default_factory=dict)` to `TokenUsage`.
  - Updated `TokenAccumulator` to accumulate prompt, completion, and total tokens per stage alongside global totals.
  - Retained backward-compatible top-level keys for all response bodies and `X-Token-Usage` headers.

* **Pipeline Versioning & Audit Logging ([`apps/api/prompts.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/prompts.py), [`apps/api/audit.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/audit.py)):**
  - Introduced `PIPELINE_VERSION = "s4.0"` and `PROMPT_VERSIONS: dict[str, str]` tracking version labels for every prompt template.
  - Recorded pipeline and prompt versions directly into each `generation_logs` Firestore document.

* **Pipeline Execution Decoupling ([`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py)):**
  - Extracted pure async functions `run_stage1` and `run_stage2` (and `run_stage2_single_script`) from FastAPI route handlers.
  - Allows evaluation runners and offline testing to execute pipeline stages directly in Python without spinning up HTTP servers or mocking Starlette request contexts.

---

### 2. Evaluation Suite & Benchmark Fixtures

* **Top 12 Bangladesh Advertiser Fixtures ([`apps/api/evals/products/`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/products)):**
  - Cleaned and generated 12 standardized JSON fixtures based on top advertising brands in Bangladesh:
    1. *Radhuni Biryani Masala 40g* (Food & Beverage)
    2. *Ispahani Mirzapore Best Leaf Tea 200g* (Food & Beverage)
    3. *Walton Non-Frost Inverter Refrigerator 347L* (Home Appliances)
    4. *Pepsodent Sensitive Expert Professional Toothpaste 140g* (Personal Care)
    5. *PRAN Mango Fruit Drink Tetra Pack* (Food & Beverage)
    6. *Taaga Flared Maroon Cotton Long Dress* (Fashion)
    7. *Apex Maverick Men's Suede Loafers* (Fashion / Footwear)
    8. *Fresh Fortified Soyabean Oil 5L* (Food & Beverage)
    9. *RFL Knock-Down Multi-Drawer Wardrobe* (Home & Living)
    10. *bKash Mobile Financial Services App* (FinTech)
    11. *10 Minute School Ghore Boshe Spoken English Course* (EdTech)
    12. *Shajgoj 100% Authentic Beauty & Skincare Retail App* (E-Commerce)
  - Paired each fixture with its real photo in [`apps/api/evals/products/images/`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/products/images) (WebP & JPEG).

* **Deterministic Metric Evaluator ([`apps/api/evals/metrics.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/metrics.py)):**
  - Pure Python metric calculator (0ms, no LLM call):
    - Total words count (punctuation-stripped whitespace split).
    - Hook length (line 1 word count).
    - Sequential line ID ordering (1..N) and kind transitions (`hook` first, `cta` last, no intermediate hooks).
    - Reason citation contiguity and valid reference checks.
    - Banned infomercial cliché detection across English and Bengali phrase lists.
    - Bengali Unicode character ratio (`\u0980` to `\u09FF`).
    - Repetition / degeneration loop detection (consecutive repeated characters $\ge 4$ and lexical diversity).

* **Evaluation CLI Runner ([`apps/api/evals/run.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/run.py)):**
  - CLI options: `--label <label>`, `--mock` (offline simulation), `--format <ugc|commercial_30s>`, `--language <all|en|bn>`, and `--limit <N>`.
  - Automatically loads and sends each product's real image bytes to Vertex AI for multi-modal analysis.
  - Writes outputs to `apps/api/evals/results/<label>/report.md` (Markdown scorecard) and `results.jsonl` (raw telemetry and script payloads).

* **Human Review Rubric ([`apps/api/evals/rubric.md`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/rubric.md)):**
  - 1-to-5 scoring guide covering Hook Strength, Creator Voice vs. Ad Voice, Specificity vs. Trivia Dumping, Persona Fit, and Natural CTA.
  - Outlines the blind A/B pairwise evaluation protocol for judging future updates against the Baseline.

---

### 3. Bengali Degeneration Loop Diagnosis & Plan Update

* **The Problem:** In product #4 (*Pepsodent Sensitive Expert*), Script 2 collapsed into a severe repetitive token loop (`"অকক অকককক ককককককককককক..."`), burning over 3,000 output tokens.
* **Root Cause:** Current prompt rules forbade transliteration into Bengali script (*"no Banglish"*) while also forbidding Latin-script English. When faced with complex clinical terms (*Hydroxyapatite, remineralization, dentine tubules*), the model encountered a perplexity trap and entered an autoregressive repetition mode collapse on the `ক` consonant.
* **Additions to [`ideas.plans.md`](file:///home/bast0k/projects/ug-script-writer/docs/sprints/4.%20Pipeline%20optimization%20/ideas.plans.md):**
  - Added repetition loops as an explicit target problem in Section 1.
  - Added Hard Validation Check in Section 6.1: regex `r'(.)\1{3,}'`, phrase n-gram loops, and low lexical diversity.
  - Added targeted recovery prompt and lower temperature (`temperature=0.2`) on retries in Section 6.2.
  - Clarified Section 9.2: explicitly permit phonetic Bengali-script transliteration for technical, brand, and ingredient loanwords to eliminate the prompt trap.
  - Added `check_repetition_loops` to [`metrics.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/metrics.py).

---

### 4. Canonical Baseline Findings

Running the eval harness live on Vertex AI across all 12 products (36 scripts) produced the baseline report:

* **Hook Brevity Pass Rate ($\le 12$ words):** **`8.3%`** (Average hook: **15.0 words**). Proves that prompt instructions alone fail to stop rambling openings.
* **Banned Cliché Violations:** **`2 hits`** (5.6% of scripts).
* **Structure Pass Rate:** **`91.7%`** (some non-sequential or non-contiguous reason citations).
* **Word Count Range Pass Rate (60-90 words):** **`100.0%`** (Average: **72.6 words**).
* **Bengali Script Ratio:** **`0.985`**.
* **Average Latency:** **`7.51s`** (TTFC) / **`18.18s`** (Total pipeline).
* **Tokens per Product:** **`13,705`** tokens.

---

### 5. Test Suite Verification

* Added [`apps/api/tests/test_evals.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_evals.py) covering word counts, Bengali ratio, banned phrases, repetition loops, and mock harness smoke runs.
* Executed full test suite: **39 passed, 0 failed** in 7.91s.

---

## Log Entry: Phase 1 Deterministic Validation & Single Retry

**Date**: 2026-11-11  
**Status**: Phase 1 Complete & Verified with Full Evaluation Run  
**Evaluation Report**: [`apps/api/evals/results/phase1_validation/report.md`](file:///home/bast0k/projects/ug-script-writer/apps/api/evals/results/phase1_validation/report.md)

### 1. In-Code Validator Engine ([`apps/api/validation.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/validation.py))

* **Deterministic Validation (`validate_script`):**
  - Implemented 0ms pure Python validation evaluating scripts against deterministic quality constraints:
    - **Hook Brevity:** Hook must be $\le 10$ words (hard rejection at $> 12$ words).
    - **Word Count Range:** Strict range enforcement ($\pm 10\%$ tolerance, 54–99 words).
    - **Structure & Ordering:** First line must be `hook`, last line must be `cta`, no intermediate hooks. Sequential line IDs 1..N.
    - **Reason Citations:** Exactly 3 reasons; referenced `line_ids` must exist and be contiguous without overlapping.
    - **Banned Clichés:** Scans line text against English & Bengali infomercial cliché lists.
    - **Repetition & Loop Collapse:** Scans for character repeats $\ge 4$, repetitive n-grams, or low lexical diversity ($< 0.45$).
    - **Script Ratio:** Ensures Bengali scripts maintain $\ge 65\%$ Bengali Unicode characters.
  - Returns structured `ValidationResult` containing hard issues, soft warnings, and `quality_flags`.

* **Targeted Recovery Prompts:**
  - `build_correction_prompt`: Formats exact numbered violation feedback ("Hook was 16 words, maximum allowed is 10 words") and previous script output.
  - Dynamically lowers temperature to `0.2` if repetition loops are detected to collapse entropy and break degenerate sampling loops.

* **Safe Execution Wrapper (`ask_validated`):**
  - Calls Gemini for generation; runs validator on output.
  - If valid: returns immediately (zero latency penalty for passing scripts).
  - If hard violations are detected: triggers a single correction retry with violation feedback.
  - Returns the best attempt with remaining issues recorded as `quality_flags` (never 500s or crashes user experience).
  - Also added `validate_reason_lines_rewrite` and `build_reason_lines_correction_prompt` for reason line regeneration endpoints.

### 2. API Integration ([`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py))

* Integrated `ask_validated` into:
  - `run_stage2_single_script` (Stage 2 parallel script generation).
  - `/regenerate/script` (full script rewrite).
  - `/regenerate/section` (hook/cta sectional rewrite).
  - `/regenerate/reason-lines` (body reason lines rewrite).

### 3. Test Suite Verification ([`apps/api/tests/test_script_validation.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_script_validation.py))

* Added 11 focused test cases covering:
  - Valid scripts passing without issues.
  - Hook length violations and correction prompt generation.
  - Structure order and non-contiguous reason citations.
  - Banned cliché detection in English and Bengali.
  - Repetition loops and temperature dropping to 0.2.
  - Bengali script ratio checks.
  - Single retry behavior, returning best attempt, and `quality_flags`.
  - Reason lines rewrite validation.
* Full test suite execution: **50 passed, 0 failed** in 7.27s.

### 4. Evaluation Benchmark Results: Baseline vs. Phase 1

Live evaluation across all 12 Bangladesh advertiser products (36 scripts generated):

| Metric | Baseline (Phase 0) | Phase 1 Validation | Delta / Target |
| :--- | :---: | :---: | :--- |
| **Hook Brevity ($\le 12$ words)** | **`8.3%`** (15.0w avg) | **`100.0%`** (8.3w avg) | **+91.7%** (Target: $\ge 90\%$) ✅ |
| **Repetition Loop Violations** | **`1 hit`** (Pepsodent) | **`0 hits`** (0.0%) | **Eliminated** (Target: 0 hits) ✅ |
| **Structure Pass Rate** | **`91.7%`** | **`97.2%`** | **+5.5%** (Target: $\ge 95\%$) ✅ |
| **Hard Rules Pass Rate** | — | **`86.1%`** | (Target: $\ge 90\%$) |
| **Word Count Range Pass Rate** | **`100.0%`** (72.6w avg) | **`88.9%`** (62.8w avg) | Within target ($\ge 85\%$) ✅ |
| **Banned Cliché Violations** | **`2 hits`** (5.6%) | **`1 hit`** (2.8%) | Dropped by 50% |
| **Bengali Script Ratio** | **`0.985`** | **`0.988`** | Optimal ✅ |

---

## Log Entry: Phase 2 Facts, Angles & Segment Gating (Two-Tier Grounding)

**Date**: 2026-11-11  
**Status**: Phase 2 Complete, Tested & Integrated into UI  

### 1. Two-Tier Schema Architecture ([`apps/api/schemas.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/schemas.py))

* **Structured `Fact` Model:**
  - Added `Fact` schema with `id: int`, `text: str`, and `value: Literal["core", "visual", "trivia"]`.
  - Added `coerce_facts_list` validator to maintain 100% backward compatibility for legacy `list[str]` payloads.
* **Creative `Angle` Model:**
  - Defined `AngleType`:
    - **Claim-bearing:** `benefit`, `demo`, `objection` (must cite $\ge 1$ verified fact ID in `based_on`).
    - **Framing:** `use_moment`, `identity`, `contrast`, `audience_context` (situational context; cannot make unsupported claims).
  - Defined `Angle` schema with `id`, `type`, `text`, `based_on: list[int]`, and `source: "model" | "user"`.
* **Grounded `Segment` Model:**
  - Added `lead_angle_ids: list[int]` to `Segment` mapping target customer personas to specific creative angles.
  - Added `product_appearance: str` and `angles: list[Angle]` to `Segments` and `GenerateResponse`.

### 2. Deterministic Grounding & Gating Engine ([`apps/api/grounding.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/grounding.py))

* **`sanitize_references`:**
  - Drops nonexistent fact IDs from angle references.
  - Drops claim-bearing angles left without valid fact grounding.
  - Filters out dangling angle IDs from segment lead angles.
* **`gate_and_repair_segments`:**
  - Gating check ensures every customer segment possesses at least one claim-bearing lead angle.
  - Automatically assigns prioritized claim-bearing fallbacks (`benefit` > `demo` > `objection`) if a segment is missing one.
  - Synthesizes a grounded benefit from core facts if no claim-bearing angles were generated.
* **`build_segment_script_context`:**
  - Isolates all `core` facts + any `visual` or `trivia` facts explicitly cited by the segment's lead angles.
  - Eradicates irrelevant packaging trivia from contaminating script generation.
* **`format_grounding_prompt_block`:**
  - Formats facts and angles cleanly for Gemini prompts with explicit two-tier separation.

### 3. Prompt & Generation Pipeline Updates ([`apps/api/prompts.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/prompts.py), [`apps/api/main.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/main.py))

* Updated `SEGMENT_PROMPT` (version `v2.0`): Multi-modal extraction now simultaneously extracts categorized facts, photo-derived product appearance, 8-12 diverse creative angles, and 3 differentiated segments with assigned lead angles.
* Updated `SCRIPT_PROMPT` and `REWRITE_SCRIPT_PROMPT` (version `v2.0`): Injected two-tier grounding rule: claims must trace to facts; situations and objections come from creative angles.
* Wired grounding and gating into `run_stage1`, `run_stage2`, `/generate`, `/generate-stream`, `/regenerate/script`, and `/regenerate/section`.

### 4. Frontend Angle Presentation & Lead Angle Badging

* **Creative Angles UI ([`apps/web/src/components/AngleChips.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/AngleChips.tsx)):**
  - Built an interactive, styled creative angles panel directly beneath verified facts in `ResultsView.tsx`.
  - Filter tabs: `All`, `Claim-bearing`, and `Framing`.
  - Category badges with distinct color accents for Benefit, Visual Demo, Objection, Moment, Identity, Contrast, and Context.
  - Direct fact reference pills (e.g. `Fact #1, #3`) indicating exactly which product facts ground each claim-bearing angle.
* **Segment Card Lead Angle Badging ([`apps/web/src/components/SegmentCard.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/SegmentCard.tsx)):**
  - Segment cards now clearly display their assigned `Lead Angles`, showing viewers which psychological hooks and objections shaped each audience segment's script.
* **Fact Significance Indicator ([`apps/web/src/components/FactChips.tsx`](file:///home/bast0k/projects/ug-script-writer/apps/web/src/components/FactChips.tsx)):**
  - Displays low-key tags for `visual` and dimmed dashed border for `trivia` facts.

### 5. Verification & Testing

* Added [`apps/api/tests/test_grounding.py`](file:///home/bast0k/projects/ug-script-writer/apps/api/tests/test_grounding.py) covering reference sanitization, segment gating, context building, prompt formatting, and legacy string coercion (6/6 passing).
* Full backend test suite: **56 passed, 0 failed** in 6.98s.
* Frontend build (`bun --filter web build`): **0 errors**, clean production build.
* Live Vertex AI pilot run verified 100% hard pass rate with creative divergence across segments.


