# UG-Scripts Sprint 4: Quality Ideas

> Last updated: 2026-11-11
> Scope: ideas for improving generated script quality, plus the planned Scenes feature. Builds on `project-context.md`.

---

## 1. Goals and Observations

**Sprint 4 goal:** raise the quality of generated scripts, not just speed and cost.

Recurring quality problems in the current pipeline:

- **Bland source material.** The Stage 2 rule "use only the facts above" protects against invented claims, but it also pushes scripts toward label-level details (colors, packaging text, trivial specs) instead of persuasive material.
- **Ad voice instead of creator voice.** Scripts tend toward third-person hooks and stock ad phrases ("my secret is", "click the link below", "upgrade your...") even when the intent is UGC.
- **Rules not enforced.** Length, duration and hook-timing rules live only in the prompt, so outputs regularly drift outside them (word count over the 60-90 range, hooks that run well past 3 seconds).
- **Feature dumping.** Scripts list several product features in one line with no story or persona relevance, because every script sees the same flat fact list.
- **Weak segment grounding.** Stage 1 can produce a segment that no product fact or angle supports.
- **One-size-fits-all format.** The product needs to support both UGC scripts and 30s commercial scripts, which differ in voice and structure.

---

## 2. Facts vs. Angles

Split grounding into two tiers: **facts limit what a script may claim; angles supply what it may talk about.**

The Stage 2 rule changes from "use only the facts above" to:

> Every claim about the product must trace to a fact. Situations, scenes, feelings, objections and demonstrations come from the angles and your own creativity.

- **Facts (hard tier):** verifiable from the description or photo. Only these can be stated as product claims.
- **Angles (soft tier):** derived framing material. Never a guaranteed claim.

| Angle type | What it covers | Example (apparel product) |
| --- | --- | --- |
| Benefit inferred from a fact | A consequence of a verified fact | Breathable fabric means no stuck-to-your-back feeling on a crowded commute |
| Usage moment | When and where it is used | The 8am commute, a Friday office day, a summer wedding |
| Objection plus answer | A hesitation and its resolution | "Linen wrinkles" answered by the relaxed fit, so a lived-in look is the point |
| Sensory or demo moment | Something visible or tangible | Pinching the fabric, holding it to the light, standing in front of a fan |
| Identity or emotional payoff | How the buyer wants to feel or be seen | Looking effortless while everyone else looks wilted |
| Audience context | Local or situational reality | Humid summers, festival season, no AC in transit |

### Related changes

- **Rank facts** by persuasion value (`core`, `visual`, `trivia`). Trivia such as colors or small design details can be a visual detail but never a line's main point. Seller-provided description claims outrank photo-derived ones.
- **Editable angles.** Reuse the existing editable fact chips for angles, so a user who knows a real customer complaint can inject the best material themselves.
- **Segment-to-angle mapping.** Each segment lists which angles it should lead with.
- **Segment gating.** A segment with no supporting fact or angle is rejected or regenerated.

### Schema sketch (not final)

```python
class Angle(BaseModel):
    type: Literal['benefit', 'moment', 'objection', 'demo', 'emotion', 'context']
    text: str
    based_on: list[int]   # indices into product_facts; empty only for pure audience context

class Segments(BaseModel):
    product_facts: list[Fact]   # Fact: text + value ('core' | 'visual' | 'trivia')
    angles: list[Angle]
    segments: list[Segment]     # each lists the angle indices to lead with
```

The `based_on` field is the guardrail: an angle with no fact behind it can only be audience context, never a product claim. Angles are also the raw material for Scenes (section 6).

---

## 3. Format Setting (UGC vs. 30s Ad)

Add a **Format** field. UGC and a 30s ad differ in structure as well as voice, so this is more than a tone switch.

| | UGC | 30s Ad |
| --- | --- | --- |
| Voice | First-person, imperfect, one person to camera | Polished brand voice, narrator or voiceover allowed |
| Hook | Scroll-stop within 3s | Strong opening image or idea, more room to build |
| Structure | hook, concept, cta | Often scenes: cold open, problem, product as hero, tagline and end card |
| Per-line extras | Optional shot cue | Speaker (VO / on-camera / on-screen text) and visual |
| Language | Code-mixing is natural | More standard, polished language |
| Platforms | TikTok, Reels, Shorts | Facebook, YouTube pre-roll, TV |
| Length | About 60-90 words | About 65-80 words |

### Design decisions

- **Name it Format, not Tone.** Tone already means the four rephrase tones (punchy, casual, authentic, direct). Two things called tone would confuse the UI and the prompts. Punchy and direct still apply to both formats.
- **Format applies to each generation run, not to the product.** The same product can be regenerated in a different format.
- **One `SCRIPT_PROMPT` plus an injected `FORMAT_SPEC`**, the same way the language block is injected. Each spec holds voice rules, structure, length, hook styles, banned phrases and 2-3 few-shot examples. A third format later is one dict entry.
- **Parameterize Stage 1.** `SEGMENT_PROMPT` currently says "short-form UGC video ads (TikTok, Reels, Shorts)", which biases personas and platforms toward UGC. That phrase should come from the format.
- **Different hook styles per format.** UGC keeps Curiosity Question, Problem Callout and Demo / Before-After. Ads could use Cold-open scene, Slice of life and Product-as-hero.
- **Schema.** Add optional `speaker` and `visual` to `Line` for every format. UGC can leave them empty, and the frontend renders only what is present.
- **Per-format validation.** The 3-second hook rule applies to UGC only.
- **Relax "no Banglish" for UGC.** Creators naturally code-mix common English words written in Bengali script. Keep it stricter for ads.
- **Future:** high-performing examples from our own dataset can feed the few-shot slots in `FORMAT_SPEC`.

---

## 4. Pipeline Changes

Most of the quality gain comes from adding a planning step, enforcing rules in code, and giving the model real examples of the voice we want.

1. **Angle-brief step between Stage 1 and Stage 2.** A cheap per-segment brief: the 2-3 facts and angles to lead with, the single core promise, the visual proof moment, and the objection to handle. Each script only receives the material relevant to its persona, which fixes feature dumping. It also makes the `reasons` real, because the technique plan exists before the lines are written instead of being justified afterwards.
2. **Validate in code, retry once.** Check word count and estimated duration, hook length (UGC), that line IDs exist and are contiguous, and that the last line is a CTA. On failure, retry with the specific violation in the prompt. A Bengali Unicode ratio check can confirm the script is in the requested language.
3. **Critique-and-rewrite pass (Stage 3).** Score each script on a rubric: hook strength, specificity, persona fit, fact compliance, creator voice. Rewrite only below a threshold. It can run per script as each finishes, either upgrading the script after the user has seen the first version, or holding the emit until the check passes.
4. **Few-shot examples and a banned-phrases list**, held in `FORMAT_SPEC`. Instructions like "natural, never stiff" do not work well on their own. Starter banned phrases: "secret", "game changer", "click the link below", "upgrade your".
5. **Shot or action cues per line** (a `visual` field), so Demo / Before-After hooks work and scripts are filmable. This overlaps with Scenes.
6. **Schema field order.** Put planning fields (technique, core promise) before `lines` in the structured output so the model commits to a plan first.
7. **Temperature split.** 0.2 for Stage 1 extraction, about 0.7 for hooks and rephrasing.

Already in the Sprint 4 backlog and still worthwhile, but lower priority than quality: Vertex AI context caching, per-stage token telemetry, and word pacing estimates for Bangla versus English.

---

## 5. Eval Set and Ranking

Without an eval set there is no way to tell whether the angle step, the critique pass or new few-shot examples actually help. It also makes it possible to test cheaper models later.

- **Hand-built starter set:** about 10 products across categories, each run in both formats and both languages, scored against a rubric.
- **Per-format rubric.** UGC and ads need different criteria, otherwise ad scripts get graded as if they were UGC. Draft criteria: hook strength, specificity, persona fit, fact compliance, voice (creator vs. brand), filmability.
- **Ranking from demo access.** Demo users are already logged against access codes in Firestore (`generation_logs`). Adding a lightweight rating on each script (for example thumbs up/down or a 1-5 score, plus saves and copies as implicit signals) turns real usage into a dataset.
- **Uses of the dataset:** regression checks when prompts change, a source of high-performing few-shot examples for `FORMAT_SPEC`, and a benchmark for model comparisons.

---

## 6. Scenes (Next Feature)

Scenes add visual, action-based directions alongside each script. It is its own stage, triggered by a button, and the descriptions should be detailed enough to feed an AI image or video generator for rapid prototyping later.

**Inputs:** the finished script, the segment, the facts, the angles and the Format. Angles matter most here: usage moments and demo moments are already visual, and fact-backed claims remain the only product claims.

### What a scene should contain

- Which script lines it covers (`line_ids`), so scenes stay tied to the script and to the reasons.
- Setting and time of day, subject and wardrobe, the action as a verb-driven beat (what physically happens), props and product placement, camera framing and movement, lighting and mood, duration, and any on-screen text.
- Visuals only. No abstract directions like "convey comfort"; describe what the camera sees.

### Decisions made

- **Scenes and lines are not one-to-one.** A scene can span several lines, and a single line can span multiple scenes.
- **Scenes are saved with the script.**
- **Model-neutral at first.** Prompts are not tuned to a specific image or video model yet.

### Design ideas for AI prototyping

- **Consistency block per script:** one short "look bible" (character description, wardrobe, location, lighting, color mood) repeated into every scene prompt so generated images and clips match each other.
- **Two outputs per scene:** a human-readable direction for the creator, and a self-contained generator prompt with no references like "same as before", since image and video models take each prompt in isolation.
- **Product accuracy:** the product's real appearance (from the photo and the extracted visual facts) must be restated in every scene, and scenes must not show features the product does not have.
- **Format-aware:** UGC scenes are phone-shot, handheld, real locations. Ad scenes can be cinematic, with a wider range of settings and camera moves. This lives in `FORMAT_SPEC`.
- **Local context:** settings and people should fit the market, not generic stock scenes.
- **Per-scene regeneration**, reusing the granular-regeneration pattern already in place for lines and reasons, plus the same rate limiting.
- **Cost:** scenes are an extra Gemini call per script, so per-stage token telemetry should cover them.

---

## 7. Suggested Order

1. Stage 1: ranked facts plus angles, and segment gating. Biggest quality jump, independent of Format, and the base for Scenes.
2. Code validation with a single retry (word count, duration, hook length, line IDs, CTA last).
3. Ratings on scripts in Firestore, to start collecting the dataset early. The starter eval set can follow.
4. `FORMAT_SPEC` with UGC first (banned phrases, few-shot examples), then the 30s Ad spec, with the `speaker` and `visual` schema fields.
5. Angle-brief planning step, then the critique-and-rewrite pass, measured against the eval set.
6. Scenes stage, built on angles and the Format spec.

---

## 8. Open Questions

- **Angle controls:** should users be able to mark angles as "must use" or "avoid"? Decision: wait until we have generated some angles and seen how they look.
- **First emit vs. validation:** hold the first emit until validation passes, or show the first draft and upgrade it in place? Undecided.
- **Rating signal:** which signal is cheapest to collect and most useful (thumbs, 1-5 score, saves and copies)? Undecided.