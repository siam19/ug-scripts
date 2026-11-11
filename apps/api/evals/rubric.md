# Script Quality Evaluation Rubric (Human Review)

Use this rubric when evaluating generated scripts or conducting blind pairwise evaluations (comparing Baseline vs. New Pipeline versions).

Score each script from **1 (Poor / Unacceptable)** to **5 (Exceptional / Ready to Film)** across the following 5 dimensions.

---

### 1. Hook Strength & Thumb-Stop Rate (1-5)
* **5 (Exceptional)**: Immediately disrupts the scroll in under 3 seconds (<= 10 words). Creates genuine curiosity, high-stakes problem callout, or visual intrigue without sounding clickbaity.
* **4 (Good)**: Clear hook that addresses a real viewer problem, but slightly wordy (11-14 words).
* **3 (Average)**: Conventional opener. Identifies the problem but uses familiar tropes.
* **2 (Weak)**: Generic or passive question ("Have you ever wanted...", "Introducing...").
* **1 (Fails)**: No hook, confusing premise, or uses forbidden infomercial clichés ("Are you tired of...", "Stop scrolling right now").

---

### 2. Authentic Creator Voice vs. Ad Voice (1-5)
* **5 (Exceptional)**: Sounds like an authentic TikTok or Reels creator sharing an unscripted discovery with a close friend. Natural cadence, casual transitions, zero corporate fluff.
* **4 (Good)**: Conversational and relatable, with only 1 line sounding slightly scripted.
* **3 (Average)**: Pleasant dialogue but lacks distinct personality; reads like a polite spokesperson.
* **2 (Stiff)**: Announcer-style presentation; overuses buzzwords ("revolutionary", "game-changer", "must-have").
* **1 (Fails)**: Full 1990s TV infomercial with cheesy urgency and forced claims.

---

### 3. Specificity vs. Trivia Dumping (1-5)
* **5 (Exceptional)**: Embeds tangible, benefit-driven product proof (e.g. "locks in moisture without greasiness in Dhaka humidity") seamlessly into creator experience.
* **4 (Good)**: Cites specific facts and benefits naturally, with minimal spec clutter.
* **3 (Average)**: Mentions product features, but lists them consecutively ("It has X, Y, and Z").
* **2 (Trivia Dumping)**: Mechanically recites irrelevant label trivia (e.g. bottle volume, packaging colors, zipper lengths) that does not persuade.
* **1 (Hallucinatory)**: Invents unsupported claims, prices, or numbers absent from the product description.

---

### 4. Persona & Market Resonance (1-5)
* **5 (Exceptional)**: Perfectly captures the target segment's daily reality, vocabulary, and frustrations (e.g., commute heat, humidity, office AC dryness).
* **4 (Good)**: Addresses the segment's core pain point clearly with appropriate cultural/market context.
* **3 (Average)**: Generic audience appeal; could apply to almost anyone.
* **2 (Mismatched)**: Uses tone or terminology inappropriate for the defined demographic.
* **1 (Tone Deaf)**: Contradicts the segment's stated motivations or situation.

---

### 5. Natural CTA & Frictionless Next Step (1-5)
* **5 (Exceptional)**: Organic, creator-authentic sign-off giving a specific reason to act (e.g. "Check the link before the current batch sells out").
* **4 (Good)**: Clear, low-pressure call to action fitting the platform.
* **3 (Average)**: Standard "link in bio" or "check out the link below".
* **2 (Aggressive)**: Pushy or desperate sales pitch.
* **1 (Missing / Broken)**: No call to action, or promises fake promo codes and non-existent discounts.

---

## Blind Pairwise Evaluation Protocol

When comparing a prompt or pipeline change against the Baseline:
1. Label the two candidates anonymously as **Script A** and **Script B** (randomizing order).
2. Rate both scripts on the 5 criteria above.
3. Select an overall winner: **A Wins**, **B Wins**, or **Tie**.
4. A pipeline update is considered a confirmed quality lift if it wins a majority of blind evaluations across the 10 test products.
