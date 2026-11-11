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
